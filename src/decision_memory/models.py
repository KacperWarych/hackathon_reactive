from __future__ import annotations

import sys
import threading

import numpy as np

from .config import ROOT, Config, atomic_json, data_root, device, digest, revisions

TASK = "Retrieve conversation excerpts that provide evidence for the question, including relevant changes and dates."


def setup_models(download=True):
    data_root()
    from huggingface_hub import HfApi, snapshot_download
    path = ROOT / "models.lock.json"
    if not path.exists():
        atomic_json(path, {m: HfApi().model_info(m).sha for m in (Config().embedding, Config().reranker)})
    locked = revisions()
    if download:
        for model, rev in locked.items():
            snapshot_download(model, revision=rev, allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model"])
    return locked


class Models:
    def __init__(self, config: Config):
        data_root()
        self.config = config
        self.revisions = revisions()
        self.device = device()
        self._embedding = self._reranker = self._tokenizer = self._rank_tokenizer = None
        self.lock = threading.RLock()

    @property
    def key(self):
        return digest({"model": self.config.embedding, "revision": self.revisions[self.config.embedding],
                       "pooling": "last-token-normalized-v1"})

    @property
    def tokenizer(self):
        if self._tokenizer is None:
            from transformers import AutoTokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.config.embedding, revision=self.revisions[self.config.embedding], padding_side="left")
        return self._tokenizer

    def _load(self, ranking=False):
        import torch
        from transformers import AutoModel, AutoModelForCausalLM, AutoTokenizer
        name = self.config.reranker if ranking else self.config.embedding
        model_type = AutoModelForCausalLM if ranking else AutoModel
        model = model_type.from_pretrained(
            name, revision=self.revisions[name], torch_dtype=torch.float32 if self.device == "cpu" else torch.float16,
            attn_implementation="sdpa").to(self.device).eval()
        if ranking:
            self._rank_tokenizer = AutoTokenizer.from_pretrained(
                name, revision=self.revisions[name], padding_side="left")
        return model

    def _forward(self, model, encoded, ranking=False):
        import torch
        with torch.inference_mode():
            try:
                return model(**encoded.to(self.device), use_cache=False, **({"logits_to_keep": 1} if ranking else {}))
            except RuntimeError as error:
                if self.device != "mps" or not any(s in str(error).lower() for s in ("mps", "out of memory")):
                    raise
                print("MPS inference failed; switching models to CPU.", file=sys.stderr)
                self.device = "cpu"
                for loaded in (self._embedding, self._reranker):
                    if loaded is not None:
                        loaded.to("cpu").float()
                torch.mps.empty_cache()
                return model(**encoded.to("cpu"), use_cache=False,
                             **({"logits_to_keep": 1} if ranking else {}))

    def embed(self, texts, query=False):
        import torch
        if not texts:
            return np.empty((0, 1024), dtype=np.float32)
        with self.lock:
            if self._embedding is None:
                self._embedding = self._load()
            if query:
                texts = [f"Instruct: {TASK}\nQuery: {t}" for t in texts]
            result = []
            for i in range(0, len(texts), self.config.batch_size):
                enc = self.tokenizer(texts[i:i+self.config.batch_size], padding=True, return_tensors="pt")
                if enc.input_ids.shape[1] > 2048:
                    raise ValueError("Embedding input exceeds 2048 tokens; rechunk or shorten the question.")
                hidden = self._forward(self._embedding, enc).last_hidden_state[:, -1]
                vector = torch.nn.functional.normalize(hidden.float(), dim=1)
                result.append(vector.detach().cpu().numpy())
            vectors = np.concatenate(result).astype(np.float32)
            if not np.isfinite(vectors).all():
                raise RuntimeError("Non-finite embeddings; rerun with MEMORY_DEVICE=cpu.")
            return vectors

    def rerank(self, question, documents):
        import torch
        if not documents:
            return []
        with self.lock:
            if self._reranker is None:
                self._reranker = self._load(ranking=True)
            tok = self._rank_tokenizer
            prefix = ('<|im_start|>system\nJudge whether the Document meets the requirements based on the Query '
                      'and the Instruct provided. Note that the answer can only be "yes" or "no".'
                      '<|im_end|>\n<|im_start|>user\n')
            suffix = '<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n'
            prompts = [f"{prefix}<Instruct>: {TASK}\n<Query>: {question}\n<Document>: {d}{suffix}" for d in documents]
            result = []
            for i in range(0, len(prompts), self.config.rerank_batch_size):
                enc = tok(prompts[i:i+self.config.rerank_batch_size], padding=True, return_tensors="pt")
                if enc.input_ids.shape[1] > 4096:
                    raise ValueError("Reranking input is too long; shorten the question.")
                logits = self._forward(self._reranker, enc, ranking=True).logits[:, -1].float()
                scores = logits[:, tok.convert_tokens_to_ids("yes")] - logits[:, tok.convert_tokens_to_ids("no")]
                if not torch.isfinite(scores).all():
                    raise RuntimeError("Non-finite reranker scores; rerun with MEMORY_DEVICE=cpu.")
                result.extend(scores.detach().cpu().tolist())
            return result
