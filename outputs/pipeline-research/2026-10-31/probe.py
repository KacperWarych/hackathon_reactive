"""Offline structural probes. No model weights, production DB, or remote API calls."""
from __future__ import annotations

import json
import hashlib
import os
import re
import tempfile
from dataclasses import replace
from pathlib import Path

from decision_memory.config import Config
from decision_memory.decision import SECTIONS, validate_decision
from decision_memory.evaluation import evidence_metrics
from decision_memory.evidence import expansion_reason, extract_options, select_options
from decision_memory.memory import Memory
from decision_memory.store import Store


class Tokenizer:
    """Whitespace tokenizer isolates control flow; does not measure real token budgets."""
    def __call__(self, text, **kwargs):
        return {"offset_mapping": [m.span() for m in re.finditer(r"\S+\s*", text)]}

    def encode(self, text, **kwargs):
        return text.split()


def run():
    result = {}
    import decision_memory
    source = Path(decision_memory.__file__).parent
    result["source_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted(source.glob("*.py"))}
    active_data = Path("/Users/kacperwarych/Desktop/hackathon reactive ai/.data")
    result["gold_source_coverage"] = {}
    for split in ("dev", "dev-large", "salesgen"):
        path = active_data / "evaluation" / f"gold-{split}.jsonl"
        if path.is_file():
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            result["gold_source_coverage"][split] = {
                "questions": len(rows), "over_six_sessions": sum(len(r["evidence"]) > 6 for r in rows),
                "maximum_sessions": max(len(r["evidence"]) for r in rows),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    retrieval = {"trace": {"candidates": [{"session_id": "gold-session"}]},
                 "evidence": [{"id": "gold-session", "text": "user: Unrelated weather."}]}
    result["session_metric_wrong_passage"] = evidence_metrics(retrieval, {"evidence": ["gold-session"]})

    question = "What is the current camera integration status?"
    rows = [
        {"text": "user: Camera integration was approved for our office printer.", "date": "2023-05-01"},
        {"text": "user: Our current camera integration status is blocked by security.", "date": "2023-05-20"},
    ]
    result["unrelated_confirmation_stops_update_search"] = {
        "question": question, "rows": rows, "expansion_reason": expansion_reason(question, rows)}

    config, tokenizer = Config(), Tokenizer()
    with tempfile.TemporaryDirectory(prefix="pipeline-research-") as work:
        os.environ["MEMORY_DATA_DIR"] = work
        store = Store(Path(work) / "memory.sqlite")
        memory = Memory(store, tokenizer, "whitespace-probe-v1")
        # Correct upstream chunk, relevant assertion in its third 200-token memory unit.
        content = " ".join(["weather"] * 400) + " I became a lighthouse keeper."
        turns = [{"role": "user", "turn_id": "occupation", "content": content}]
        full = "user: " + content + "\n"
        chunks = [{"session_id": "correct", "date": "2023-05-20", "iso": "2023-05-20",
                   "text": full, "start": 0, "end": len(full)}]
        q = {"question": "What is my current occupation?"}
        options = extract_options(q, [0], chunks, {"correct": turns}, tokenizer, config, memory)
        evidence, selected = select_options(q, options, config, tokenizer, lambda *_: 0)
        result["paraphrase_lost_during_packing"] = {
            "input_contains_answer": "lighthouse keeper" in full,
            "memory_unit_count": len(memory.records(turns[0])),
            "generated_option_count": len(options),
            "packed_contains_answer": "lighthouse keeper" in "\n".join(e["text"] for e in evidence),
            "packed_metrics": evidence_metrics({"trace": {"candidates": [{"session_id": "correct"}]},
                                                 "evidence": evidence}, {"evidence": ["correct"]})}
        # Head truncation with a supported small excerpt budget can remove the selected reply.
        turns = [{"role": "assistant", "turn_id": "offer", "content": " ".join(["proposal"] * 80)},
                 {"role": "user", "turn_id": "answer", "content": "The integration works; I accept it."}]
        full = "".join(t["role"] + ": " + t["content"] + "\n" for t in turns)
        start = full.index("user:")
        chunks = [{"session_id": "reply", "date": "2023-05-20", "text": full[start:],
                   "start": start, "end": len(full)}]
        options = extract_options({"question": "Is integration accepted?"}, [0], chunks,
                                  {"reply": turns}, tokenizer, replace(config, excerpt_tokens=60), memory)
        result["target_clipped_at_small_excerpt_budget"] = {
            "excerpt_tokens": 60, "option_count": len(options),
            "target_retained": any("accept it" in o["text"] for o in options)}
        store.close()

    # Validation is deliberately structural, so these are output-assurance limits.
    cases = {
        "negation_outside_quote": ("user: It is not true that integration works.", "integration works", "Integration resolved"),
        "different_fact": ("user: Lunch has been paid.", "Lunch has been paid.", "Integration resolved"),
    }
    result["display_validation_limits"] = {}
    for name, (text, quote, claim) in cases.items():
        obj = {section: [] for section in SECTIONS}
        obj["resolutions"] = [{"text": claim, "sources": ["E1"], "confirmation_quote": quote}]
        result["display_validation_limits"][name] = {
            "accepted": validate_decision(json.dumps(obj), [{"text": text}])[0] is not None}
    return result


if __name__ == "__main__":
    output = run()
    path = Path(__file__).with_name("probe-results.json")
    path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))
