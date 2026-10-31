"""Resumable offline preparation. Optional --live continues with the real Reactor runs."""
import argparse
import json
from pathlib import Path

from decision_memory.config import Config, atomic_json, data_root, load_env
from decision_memory.evaluation import evaluate_answers, evaluate_retrieval, freeze, manifests
from decision_memory.index import Index
from decision_memory.models import Models, setup_models
from decision_memory.reactor import export_predictions, run_questions
from decision_memory.retrieval import Retriever
from decision_memory.store import Store


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--live", action="store_true", help="After offline preparation, run validation and test through Reactor")
    p.add_argument("--downloads", type=Path, default=Path.home()/"Downloads")
    args = p.parse_args()
    load_env(); setup_models()
    store = Store()
    for split in ("dev", "test"):
        print("Importing", split, flush=True)
        print(store.ingest(args.downloads/f"{split}.tar.gz", split), flush=True)
    partitions = manifests(store)
    config = Config(); models = Models(config); index = Index(store, models, config)
    demo = json.loads((data_root()/"manifests"/"demo.json").read_text())
    print("Preparing three replayable evidence examples", flush=True)
    index.build("dev", demo["history_ids"])
    retriever = Retriever(store, models, config)
    demo_report = evaluate_retrieval(store, retriever, demo)
    for name in ("tune", "validation"):
        print("Indexing", name, flush=True)
        print(index.build("dev", partitions[name]["history_ids"]), flush=True)
    tuning = evaluate_retrieval(store, retriever, partitions["tune"])
    chosen = freeze(tuning["path"])
    validation = evaluate_retrieval(store, retriever, partitions["validation"], [chosen["mode"]])
    stress = json.loads((data_root()/"manifests"/"stress.json").read_text())
    store.ingest(args.downloads/"dev-large.tar.gz", "dev-large", set(stress["history_ids"]))
    stress_index = index.build("dev-large", stress["history_ids"])
    print(stress_index, flush=True)
    stress_report = evaluate_retrieval(store, retriever, stress, [chosen["mode"]])
    test_index = index.build("test")
    print(test_index, flush=True)
    atomic_json(data_root()/"evaluation"/"offline-summary.json", {
        "config": config.fingerprint, "selected": chosen,
        "demo": demo_report, "tuning": tuning, "validation": validation,
        "stress": stress_report, "stress_index": stress_index, "test_index": test_index,
        "test_questions": len(store.questions("test")),
        "reactor_answers": "Not measured by offline preparation; configure credentials and run live evaluation."})
    print("Offline preparation complete. Selected mode:", chosen["mode"], flush=True)
    if args.live:
        for split, qs in (("validation", store.questions("dev", partitions["validation"]["question_ids"])),
                          ("test", store.questions("test"))):
            run_id = f"{split}_{config.fingerprint[:8]}_{chosen['mode']}"
            print(run_questions(store, retriever, qs, run_id, chosen["mode"]), flush=True)
            out = data_root()/"runs"/run_id/"predictions.jsonl"
            print(export_predictions(store, run_id, out), flush=True)
            if split == "validation":
                print(evaluate_answers(store, run_id), flush=True)
    store.close()


if __name__ == "__main__":
    main()
