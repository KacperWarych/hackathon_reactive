"""Check actual Qwen offset behavior offline, without model weights."""
import json
import os
import re
import tempfile
from pathlib import Path

from transformers import AutoTokenizer

from decision_memory.memory import Memory
from decision_memory.store import Store

REVISION = "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
SNAPSHOT = Path("/Users/kacperwarych/Desktop/hackathon reactive ai/.data/models/hub/") / (
    "models--Qwen--Qwen3-Embedding-0.6B/snapshots/" + REVISION)


def run():
    tokenizer = AutoTokenizer.from_pretrained(str(SNAPSHOT), local_files_only=True, padding_side="left")
    results = {"tokenizer_revision": REVISION, "cases": {}}
    with tempfile.TemporaryDirectory(prefix="ing-real-tokenizer-") as tmp:
        os.environ["MEMORY_DATA_DIR"] = tmp
        store = Store(Path(tmp) / "memory.sqlite")
        memory = Memory(store, tokenizer, "real-qwen-" + REVISION)
        for name, separator in (("period_space", ". "), ("newline", "\n")):
            text = (" ".join(["weather"] * 70) + separator) * 6
            enc = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)
            boundaries = {m.end() for m in re.finditer(r"[.!?](?:\s+|$)|\n+", text)}
            edges = {b for a, b in enc["offset_mapping"]}
            records = memory.records({"role": "user", "content": text})
            corrected = {m.start() + 1 if text[m.start()] in ".!?" else m.end()
                         for m in re.finditer(r"[.!?](?:\s+|$)|\n+", text)}
            results["cases"][name] = {
                "tokens": len(enc["input_ids"]),
                "sentence_boundary_offsets": sorted(boundaries),
                "token_matched_boundaries": sorted(boundaries & edges),
                "punctuation_end_matched_boundaries": sorted(corrected & edges),
                "units": [{"start": r["start"], "end": r["end"],
                           "tokens": len(tokenizer.encode(text[r["start"]:r["end"]], add_special_tokens=False)),
                           "ends_at_recorded_boundary": r["end"] in boundaries,
                           "tail": text[r["start"]:r["end"]][-45:]} for r in records]}
        store.close()
    return results


if __name__ == "__main__":
    results = run()
    Path(__file__).with_name("ing-real-tokenizer-results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))
