from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import Config, data_root, digest, load_env
from .store import Store, iso_date


def manifest_arg(value):
    from .evaluation import load_manifest
    path = Path(value)
    return load_manifest(path if path.exists() else data_root() / "manifests" / f"{value}.json")


def selection(args, store):
    manifest = manifest_arg(args.manifest) if getattr(args, "manifest", None) else None
    split = manifest["split"] if manifest else args.split
    qs = store.questions(split, manifest["question_ids"] if manifest else None)
    if getattr(args, "limit", None):
        qs = qs[:args.limit]
    return qs


def selected_mode(mode, config):
    if mode != "selected":
        return mode
    path = data_root() / "evaluation" / "frozen.json"
    if not path.exists():
        raise ValueError("Run all tuning ablations and memory freeze first, or explicitly choose --mode full.")
    frozen = json.loads(path.read_text())
    if frozen["config"] != config.fingerprint:
        raise ValueError("Frozen configuration differs from this build; repeat tuning before validation/test.")
    return frozen["mode"]


def main(argv=None):
    load_env(); data_root()
    parser = argparse.ArgumentParser(description="Hybrid conversation retrieval and decision memory")
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("setup-models", help="Pin and download the two Qwen models")
    ingest = subs.add_parser("ingest")
    ingest.add_argument("--split", required=True, help="Dataset name, e.g. dev, test, or salesgen")
    ingest.add_argument("--archive", "--source", dest="archive", type=Path, help="A .tar.gz archive or dataset directory")
    ingest.add_argument("--manifest", help="Restrict imported histories (required for dev-large)")
    subs.add_parser("stats")
    subs.add_parser("manifests")
    idx = subs.add_parser("index")
    idx.add_argument("--split", default="dev")
    idx.add_argument("--manifest", action="append", default=[])
    idx.add_argument("--lexical-only", action="store_true")
    idx.add_argument("--limit-histories", type=int)
    retrieve = subs.add_parser("retrieve")
    retrieve.add_argument("--split", default="dev")
    retrieve.add_argument("--question-id")
    retrieve.add_argument("--history-id")
    retrieve.add_argument("--question")
    retrieve.add_argument("--date")
    retrieve.add_argument("--mode", default="full", choices=["bm25", "dense", "hybrid", "rerank", "full", "selected"])
    retrieve.add_argument("--out", type=Path)
    run = subs.add_parser("run")
    run.add_argument("--split", default="test")
    run.add_argument("--manifest")
    run.add_argument("--limit", type=int)
    run.add_argument("--run-id", required=True)
    run.add_argument("--mode", default="selected", choices=["bm25", "dense", "hybrid", "rerank", "full", "selected"])
    run.add_argument("--retry-uncertain", action="store_true")
    ev = subs.add_parser("evaluate")
    ev.add_argument("--manifest", default="tune")
    ev.add_argument("--modes", nargs="+", default=["bm25", "dense", "hybrid", "rerank", "full"])
    ev.add_argument("--run-id", help="Evaluate saved Reactor answers instead of retrieval")
    fr = subs.add_parser("freeze")
    fr.add_argument("report", type=Path)
    ex = subs.add_parser("export")
    ex.add_argument("--run-id", required=True)
    ex.add_argument("--out", type=Path, required=True)
    ex.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args(argv)
    store = Store()
    try:
        if args.command == "ingest":
            if args.split == "dev-large" and not args.manifest:
                raise ValueError("Use --manifest stress to avoid importing all of dev-large in v1.")
            manifest = manifest_arg(args.manifest) if args.manifest else None
            result = store.ingest(args.archive or Path.home()/"Downloads"/f"{args.split}.tar.gz", args.split,
                                  set(manifest["history_ids"]) if manifest else None)
        elif args.command == "stats":
            result = store.stats()
        elif args.command == "manifests":
            from .evaluation import manifests
            result = manifests(store)
        elif args.command == "freeze":
            from .evaluation import freeze
            result = freeze(args.report)
        elif args.command == "export":
            from .reactor import export_predictions
            result = export_predictions(store, args.run_id, args.out, args.allow_partial)
        elif args.command == "setup-models":
            from .models import setup_models
            result = setup_models()
        elif args.command == "evaluate" and args.run_id:
            from .evaluation import evaluate_answers
            result = evaluate_answers(store, args.run_id)
        else:
            from .index import Index
            from .models import Models
            from .retrieval import Retriever
            config = Config()
            if args.command == "run":
                from .reactor import credentials
                credentials()  # fail quickly without model loading
            models = Models(config)
            if args.command == "index":
                chosen = [manifest_arg(p) for p in args.manifest]
                if chosen and len({p["split"] for p in chosen}) > 1:
                    raise ValueError("Index one split at a time.")
                split = chosen[0]["split"] if chosen else args.split
                hids = sorted({h for p in chosen for h in p["history_ids"]}) if chosen else sorted({q["history_id"] for q in store.questions(split)})
                result = Index(store, models, config).build(split, hids[:args.limit_histories] if args.limit_histories else hids,
                                                           dense=not args.lexical_only)
            elif args.command == "retrieve":
                if args.question_id:
                    question = store.questions(args.split, [args.question_id])[0]
                elif args.question and args.history_id and args.date:
                    question = {"split": args.split, "history_id": args.history_id, "question": args.question,
                                "question_date": args.date, "iso": iso_date(args.date),
                                "question_id": "custom_"+digest([args.history_id, args.question, args.date])[:16]}
                else:
                    raise ValueError("Use --question-id, or --history-id with --question and --date.")
                result = Retriever(store, models, config).retrieve(question, selected_mode(args.mode, config))
                if args.out:
                    from .config import atomic_json
                    atomic_json(args.out, result)
            elif args.command == "evaluate":
                from .evaluation import evaluate_retrieval
                modes = [selected_mode(m, config) for m in args.modes]
                result = evaluate_retrieval(store, Retriever(store, models, config), manifest_arg(args.manifest), modes)
            else:
                from .reactor import run_questions
                result = run_questions(store, Retriever(store, models, config), selection(args, store),
                                       args.run_id, selected_mode(args.mode, config), args.retry_uncertain)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, RuntimeError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
