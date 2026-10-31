from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(os.environ["MEMORY_PROJECT_DIR"]).expanduser().resolve() if os.environ.get("MEMORY_PROJECT_DIR") else next(
    (p for p in Path(__file__).resolve().parents
     if (p / "pyproject.toml").is_file() and (p / "models.lock.json").is_file()), Path.cwd())


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w") as out:
        out.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
        out.flush()
        os.fsync(out.fileno())
    temp.replace(path)


@dataclass(frozen=True)
class Config:
    embedding: str = "Qwen/Qwen3-Embedding-0.6B"
    reranker: str = "Qwen/Qwen3-Reranker-0.6B"
    target_tokens: int = 450
    max_tokens: int = 600
    overlap_tokens: int = 80
    retrieve_k: int = 40
    rerank_k: int = 40
    rrf_constant: int = 60
    evidence_chars: int = 8000
    evidence_tokens: int = 2000
    max_excerpts: int = 6
    excerpt_tokens: int = 320
    context_tokens: int = 80
    expansion_k: int = 12
    max_expansion_queries: int = 1
    max_message_chars: int = 16000
    batch_size: int = 8
    rerank_batch_size: int = 4

    @property
    def fingerprint(self):
        return digest({"config": asdict(self), "models": revisions(), "pipeline_version": 3})


def revisions():
    path = ROOT / "models.lock.json"
    if not path.exists():
        raise RuntimeError("Missing models.lock.json; run memory setup-models first.")
    return json.loads(path.read_text())


def data_root() -> Path:
    p = Path(os.environ.get("MEMORY_DATA_DIR", ROOT / ".data"))
    p.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(p / "models"))
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    return p


def load_env():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)


def device() -> str:
    import torch
    chosen = os.environ.get("MEMORY_DEVICE")
    if chosen:
        return chosen
    return "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"
