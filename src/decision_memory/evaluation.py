from __future__ import annotations

import json
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from .answer_content import answer_content, has_answer_content
from .config import atomic_json, data_root, digest
from .reactor import result_path
from .retrieval import MODES
from .snapshot import is_current
from .vendor.score import answer_matched, evidence_f1


def latency_summary(values):
    values = sorted(v for v in values if isinstance(v, (int, float)))
    def percentile(fraction):
        if not values:
            return None
        position = (len(values) - 1) * fraction
        lo = int(position)
        hi = min(lo + 1, len(values) - 1)
        return values[lo] + (values[hi] - values[lo]) * (position - lo)
    return {"p50_seconds": percentile(.5), "p95_seconds": percentile(.95)}


def gold(split="dev"):
    path = data_root() / "evaluation" / f"gold-{split}.jsonl"
    return {r["question_id"]: r for r in map(json.loads, path.read_text().splitlines())}


def load_manifest(path):
    return json.loads(Path(path).read_text())


def manifests(store, seed=42):
    g = gold()
    questions = store.questions("dev")
    groups = defaultdict(list)
    for q in questions:
        groups[q["history_id"]].append(q)
    hids = sorted(groups)
    random.Random(seed).shuffle(hids)
    cutoff = round(len(hids) * .8)
    partitions = {"tune": hids[:cutoff], "validation": hids[cutoff:]}
    output = {}
    for name, pool in partitions.items():
        counts, picked, selected = Counter(), [], set()
        types = sorted({r["question_type"] for r in g.values()})
        # Prefer one abstention per type where this partition contains one.
        for abstention_first in (True, False):
            for kind in types:
                for hid in pool:
                    if hid in selected or counts[kind] >= 10:
                        continue
                    candidates = groups[hid]
                    if not any(g[q["question_id"]]["question_type"] == kind and
                               (not abstention_first or g[q["question_id"]]["abstain"]) for q in candidates):
                        continue
                    delta = Counter(g[q["question_id"]]["question_type"] for q in candidates)
                    if any(counts[t]+n > 10 for t, n in delta.items()):
                        continue
                    selected.add(hid); picked.extend(q["question_id"] for q in candidates); counts.update(delta)
                    if abstention_first:
                        break
        payload = {"name": name, "split": "dev", "seed": seed, "question_ids": sorted(picked),
                   "history_ids": sorted(selected), "question_types": dict(counts),
                   "abstentions": sum(g[q]["abstain"] for q in picked)}
        atomic_json(data_root() / "manifests" / f"{name}.json", payload)
        output[name] = payload
    assert not set(output["tune"]["history_ids"]) & set(output["validation"]["history_ids"])
    atomic_json(data_root() / "manifests" / "history-partitions.json", partitions)
    stress_ids = output["validation"]["history_ids"][:10]
    stress = {"name": "stress", "split": "dev-large", "seed": seed, "history_ids": stress_ids,
              "question_ids": [q["question_id"] for q in questions if q["history_id"] in stress_ids]}
    atomic_json(data_root() / "manifests" / "stress.json", stress)
    # Genuine records selected for capability demonstrations, never injected into retrieval.
    demos = []
    predicates = [
        ("A recorded purchase", lambda q, a: a["question_type"] == "single-session-user" and "buy" in q["question"].lower() and not a["abstain"]),
        ("A changing fact", lambda q, a: a["question_type"] == "knowledge-update" and not a["abstain"]),
        ("Insufficient evidence", lambda q, a: a["abstain"]),
    ]
    pool = [q for q in questions if q["question_id"] in output["tune"]["question_ids"]]
    for label, predicate in predicates:
        q = next((q for q in pool if predicate(q, g[q["question_id"]])), None)
        if q:
            demos.append({"label": label, "question_id": q["question_id"], "history_id": q["history_id"],
                          "question": q["question"]})
    atomic_json(data_root() / "manifests" / "examples.json", demos)
    atomic_json(data_root() / "manifests" / "demo.json", {
        "name": "demo", "split": "dev", "seed": seed,
        "question_ids": [d["question_id"] for d in demos],
        "history_ids": sorted({d["history_id"] for d in demos})})
    return output


def evidence_metrics(retrieval, annotation):
    target = set(annotation["evidence"])
    candidate_sessions = list(dict.fromkeys(c["session_id"] for c in retrieval["trace"]["candidates"]))[:20]
    packed = {e["id"] for e in retrieval["evidence"]}
    return {"recall_at_20": len(set(candidate_sessions) & target)/len(target) if target else None,
            "all_required_at_20": target <= set(candidate_sessions) if target else None,
            "packed_recall": len(packed & target)/len(target) if target else None,
            "packed_all_required": target <= packed if target else None,
            "packed_precision": len(packed & target)/len(packed) if target and packed else 0 if target else None}


def evaluate_retrieval(store, retriever, manifest, modes=MODES):
    annotations = gold(manifest["split"])
    questions = store.questions(manifest["split"], manifest["question_ids"])
    identity = digest({"manifest": manifest, "config": retriever.config.fingerprint, "modes": list(modes)})[:16]
    path = data_root() / "evaluation" / f"retrieval-{manifest['name']}-{identity}.json"
    report = json.loads(path.read_text()) if path.exists() else {
        "manifest": manifest, "config": retriever.config.fingerprint, "rows": []}
    done = {(r["question_id"], r["mode"]) for r in report["rows"]}
    for q in questions:
        for mode in modes:
            if (q["question_id"], mode) in done:
                continue
            result = retriever.retrieve(q, mode)
            if manifest["name"] == "demo":
                atomic_json(data_root()/"demos"/(digest([q["question_id"], mode])[:24]+".json"), result)
            annotation = annotations[q["question_id"]]
            report["rows"].append({"question_id": q["question_id"], "mode": mode,
                "question_type": annotation["question_type"], "abstain_gold": annotation["abstain"],
                **evidence_metrics(result, annotation), "seconds": result["trace"]["seconds"],
                "evidence_tokens": result["trace"].get("evidence_tokens"),
                "excerpt_count": result["trace"].get("excerpt_count"),
                "reranked_documents": result["trace"].get("reranked_documents"),
                "message_chars": result["trace"]["message_chars"]})
            atomic_json(path, report)
            print(f"{manifest['name']} {q['question_id']} {mode}: packed recall {report['rows'][-1]['packed_recall']}", flush=True)
    keys = ["recall_at_20", "all_required_at_20", "packed_recall", "packed_all_required", "packed_precision", "seconds",
            "message_chars", "evidence_tokens", "excerpt_count", "reranked_documents"]

    def aggregate(rows):
        return {**{key: statistics.mean(r[key] for r in rows if r.get(key) is not None)
                   if any(r.get(key) is not None for r in rows) else None for key in keys},
                **latency_summary(r["seconds"] for r in rows)}

    report["summary"] = {mode: aggregate([r for r in report["rows"] if r["mode"] == mode]) for mode in modes}
    report["by_type"] = {kind: {mode: aggregate([r for r in report["rows"] if r["mode"] == mode and r["question_type"] == kind])
                               for mode in modes} for kind in sorted({r["question_type"] for r in report["rows"]})}
    report["complete"] = len(report["rows"]) == len(questions)*len(modes)
    atomic_json(path, report)
    return {"path": str(path), "summary": report["summary"], "complete": report["complete"]}


def freeze(report_path):
    report = json.loads(Path(report_path).read_text())
    if report["manifest"]["name"] != "tune" or not report.get("complete"):
        raise ValueError("Freeze requires a completed tuning report.")
    if set(report["summary"]) != set(MODES):
        raise ValueError("Complete all five retrieval ablations before freezing a selection.")
    mode = max(report["summary"], key=lambda m: (
        report["summary"][m]["packed_recall"], report["summary"][m]["packed_all_required"],
        -report["summary"][m]["seconds"]))
    value = {"mode": mode, "config": report["config"], "tuning_report": str(report_path),
             "tuning_report_hash": digest(report), "selection": "packed recall, then complete evidence, then latency"}
    atomic_json(data_root() / "evaluation" / "frozen.json", value)
    return value


def evaluate_answers(store, run_id):
    run_dir = data_root() / "runs" / run_id
    meta = json.loads((run_dir / "run.json").read_text())
    annotations = gold(meta["split"])
    details = []
    stale = []
    for q in store.questions(meta["split"], meta["question_ids"]):
        path = result_path(run_dir, q["question_id"])
        if not path.exists():
            continue
        record = json.loads(path.read_text())
        result = record["result"]
        if result["status"] != "answered" or not has_answer_content(result.get("answer")):
            continue
        retrieval = record.get("retrieval", {})
        if not retrieval.get("question") or not is_current(store, retrieval):
            stale.append(q["question_id"])
            continue
        a = annotations[q["question_id"]]
        abstain = bool(result.get("abstained"))
        label = ("correct_abstention" if abstain else "missed_abstention") if a["abstain"] else (
            "unnecessary_abstention" if abstain else "automatic_match" if answer_matched(answer_content(result["answer"]), a) else "unjudged")
        details.append({"question_id": q["question_id"], "question_type": a["question_type"], "judgment": label,
                        "gold_abstain": a["abstain"], "predicted_abstain": abstain,
                        "evidence_f1": evidence_f1([c["id"] for c in result.get("citations", [])], a["evidence"]) if not a["abstain"] else None,
                        "latency_s": record.get("reactor_latency_s", result.get("latency_s"))})
    positive = sum(r["predicted_abstain"] for r in details)
    target = sum(r["gold_abstain"] for r in details)
    correct = sum(r["predicted_abstain"] and r["gold_abstain"] for r in details)
    latencies = [r["latency_s"] for r in details if r["latency_s"] is not None]
    report = {"run_id": run_id, "expected": len(meta["question_ids"]), "completed": len(details),
              "complete": {r["question_id"] for r in details} == set(meta["question_ids"]),
              "missing": len(set(meta["question_ids"]) - {r["question_id"] for r in details}),
              "stale": len(stale), "stale_question_ids": stale,
              "judgments": dict(Counter(r["judgment"] for r in details)), "details": details,
              "abstention_precision": correct / positive if positive else None,
              "abstention_recall": correct / target if target else None,
              "mean_latency_s": statistics.mean(latencies) if latencies else None,
              **latency_summary(latencies),
              "mean_evidence_f1": statistics.mean(r["evidence_f1"] for r in details if r["evidence_f1"] is not None) if any(r["evidence_f1"] is not None for r in details) else None,
              "note": "Automatic matches are not complete official LLM-judged accuracy. Transport failures and historical or unknown source snapshots are incomplete."}
    atomic_json(run_dir / "evaluation.json", report)
    return report
