"""Compare local evidence budgets. Does not contact Reactor or generate answer-quality scores."""
import argparse
import json
import statistics
from dataclasses import replace
from pathlib import Path

from decision_memory.config import Config, atomic_json, data_root
from decision_memory.evaluation import evidence_metrics, latency_summary
from decision_memory.models import Models
from decision_memory.retrieval import MODES, Retriever
from decision_memory.store import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", default="salesgen")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--mode", choices=MODES, default="bm25")
    parser.add_argument("--budgets", type=int, nargs="+", default=[1000, 2000, 4000])
    parser.add_argument("--max-excerpts", type=int, default=6)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.limit < 1 or args.max_excerpts < 1 or any(b < 1 for b in args.budgets):
        parser.error("Limits, excerpt count, and token budgets must be positive.")
    store = Store()
    try:
        questions = store.questions(args.split)[:args.limit]
        if not questions:
            parser.error("No questions in this split.")
        gold_path = data_root() / "evaluation" / f"gold-{args.split}.jsonl"
        gold = {r["question_id"]: r for r in map(json.loads, gold_path.read_text().splitlines())} if gold_path.exists() else {}
        models = Models(Config())
        rows = []
        for budget in args.budgets:
            config = replace(Config(), evidence_tokens=budget, evidence_chars=max(8000, budget * 6),
                             max_excerpts=args.max_excerpts)
            retriever = Retriever(store, models, config)
            for question in questions:
                result = retriever.retrieve(question, args.mode)
                trace = result["trace"]
                rows.append({"budget": budget, "question_id": question["question_id"],
                             "seconds": trace["seconds"], "message_chars": trace["message_chars"],
                             "evidence_tokens": trace["evidence_tokens"], "excerpt_count": trace["excerpt_count"],
                             "timings": trace["timings"], "cache": trace["cache"],
                             **(evidence_metrics(result, gold[question["question_id"]])
                                if question["question_id"] in gold else {})})
        summary = {}
        for budget in args.budgets:
            group = [r for r in rows if r["budget"] == budget]
            summary[budget] = {"questions": len(group), **latency_summary(r["seconds"] for r in group),
                               "mean_evidence_tokens": statistics.mean(r["evidence_tokens"] for r in group),
                               "mean_message_chars": statistics.mean(r["message_chars"] for r in group),
                               "packed_all_required": statistics.mean(r["packed_all_required"] for r in group
                                   if r.get("packed_all_required") is not None)
                                   if any(r.get("packed_all_required") is not None for r in group) else None}
        report = {"split": args.split, "mode": args.mode, "max_excerpts": args.max_excerpts,
                  "summary": summary, "rows": rows,
                  "note": "Retrieval latency only. Caches warm across budgets; inspect per-row cache/timings. "
                          "Tokens use the embedding tokenizer; Reactor token counts may differ. "
                          "Session coverage does not establish full answer accuracy."}
        atomic_json(args.out, report)
        print(json.dumps(summary, indent=2))
    finally:
        store.close()


if __name__ == "__main__":
    main()
