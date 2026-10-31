"""Non-destructive ingestion/index/config probes; active source, temporary data only."""
from __future__ import annotations

import ast
import io
import json
import os
import re
import tempfile
import tarfile
import threading
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import numpy as np

from decision_memory import config as cfg
from decision_memory import index as idx
from decision_memory.chunks import chunk_turns
from decision_memory.config import Config, digest
from decision_memory.entries import add_entry, export_entries, parse_transcript
from decision_memory.index import Index
from decision_memory.memory import Memory, cues
from decision_memory.models import Models
from decision_memory.store import Store


class Tokenizer:
    def __call__(self, text, **kwargs):
        return {"offset_mapping": [m.span() for m in re.finditer(r"\S+\s*", text)]}

    def encode(self, text, **kwargs):
        return text.split()


class FakeModels:
    tokenizer = Tokenizer()
    revisions = {Config().embedding: "audit-tokenizer-v1"}
    key = "audit-model-v1"

    def embed(self, texts, query=False):
        return np.ones((len(texts), 8), dtype=np.float32) / np.sqrt(8)


def history(hid="h1", sid="s1", text="Original camera budget.", turns=None):
    return {"history_id": hid, "sessions": [{"session_id": sid, "date": "2023-05-20",
            "turns": turns if turns is not None else [{"turn_id": "t1", "role": "user", "content": text}]}]}


def question(qid="q1", hid="h1"):
    return {"question_id": qid, "history_id": hid, "question": "What camera budget?", "question_date": "2023-06-01"}


def dataset(folder, hs, qs, gold=None):
    (folder / "public").mkdir(parents=True, exist_ok=True)
    (folder / "public/histories.jsonl").write_text("".join(json.dumps(r) + "\n" for r in hs))
    (folder / "public/questions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in qs))
    if gold is not None:
        (folder / "gold").mkdir(exist_ok=True)
        (folder / "gold/gold.jsonl").write_text("".join(json.dumps(r) + "\n" for r in gold))
    return folder


def capture(fn):
    try:
        return {"returned": fn()}
    except Exception as e:
        return {"error": type(e).__name__, "message": str(e)}


def run(work):
    out = {}
    os.environ["MEMORY_DATA_DIR"] = str(work / "data")
    store = Store(work / "memory.sqlite")
    first = dataset(work / "first", [history()], [question("q1"), question("q2")],
                    [{"question_id": "q1"}, {"question_id": "q2"}])
    store.ingest(first, "dev")
    second = dataset(work / "second", [history(text="Updated camera budget.")], [question("q1")],
                     [{"question_id": "q1"}])
    store.ingest(second, "dev")
    gold = [json.loads(s) for s in (work / "data/evaluation/gold-dev.jsonl").read_text().splitlines()]
    out["ING-01"] = {"question_ids_after_reimport": [q["question_id"] for q in store.questions("dev")],
                     "gold_question_ids": [r["question_id"] for r in gold]}
    # Supported dataset directory: export occupies histories.jsonl, questions.jsonl exists.
    sid = add_entry(store, "dev", "h1", "2023-05-25", "Customer: Camera approved.")
    exported = json.loads(export_entries(store, "dev", "h1"))
    exported_source = dataset(work / "exported", [exported], [])
    out["ING-02"] = {"exported_manual_sid": sid, "reimport": capture(lambda: store.ingest(exported_source, "dev"))}

    missing = [{"role": "user", "content": "camera budget"}]
    source = dataset(work / "missing-turnid", [history("missing", turns=missing)], [])
    out["ING-03"] = {"ingest": capture(lambda: store.ingest(source, "bad")),
                     "index": capture(lambda: Index(store, FakeModels(), Config()).build("bad", dense=False))}
    duplicate = [{"turn_id": "duplicate", "role": "user", "content": "Camera pending."},
                 {"turn_id": "duplicate", "role": "assistant", "content": "Proposed workaround."}]
    source = dataset(work / "duplicate-turnid", [history("duplicates", turns=duplicate)], [])
    out["ING-03"]["duplicate_turn_ids_ingest"] = capture(lambda: store.ingest(source, "duplicate"))
    source = dataset(work / "orphan-question", [], [question("orphan", "no-such-history")])
    out["ING-03"]["orphan_question_ingest"] = capture(lambda: store.ingest(source, "orphan"))

    # A malformed late question leaves earlier INSERT pending; unrelated commit persists it.
    malformed = dataset(work / "malformed", [history("partial")], [question("partial", "partial"),
                        {**question("invalid", "partial"), "question_date": "not-a-date"}])
    err = capture(lambda: store.ingest(malformed, "partial"))
    pending = store.db.in_transaction
    memory = Memory(store, Tokenizer(), "probe")  # executescript implicitly commits pending INSERT.
    other = Store(store.path)
    out["ING-04"] = {"ingest_error": err, "transaction_left_pending": pending,
                     "questions_visible_after_memory_init": [r["question_id"] for r in other.questions("partial")]}
    other.close()

    out["ING-05"] = {"unknown_role": parse_transcript("Customer: Camera integration blocked.\nManager: Approved the budget.")}
    out["ING-06"] = {"config": {"target_tokens": 800, "max_tokens": 600},
                     "maximum_actual_chunk_tokens": max(r["tokens"] for r in chunk_turns(
                         [{"turn_id": "a", "role": "user", "content": "word " * 2000}], Tokenizer(),
                         replace(Config(), target_tokens=800)))}
    zero = replace(Config(), batch_size=0)
    out["ING-06"]["zero_batch_index"] = capture(lambda: Index(store, FakeModels(), zero).build("dev"))

    # Same exact temp filename is reused by atomic_json's concurrent writers.
    barrier = threading.Barrier(2)
    atomic_results = []
    def sync(_fd):
        barrier.wait(timeout=10)
    def atomic_worker(n):
        atomic_results.append({"writer": n, **capture(lambda: cfg.atomic_json(work / "concurrent.json", {"writer": n}))})
    with patch.object(cfg.os, "fsync", sync):
        threads = [threading.Thread(target=atomic_worker, args=(n,)) for n in range(2)]
        for t in threads: t.start()
        for t in threads: t.join(15)
    out["ING-07"] = {"writers": atomic_results, "final": json.loads((work / "concurrent.json").read_text())}

    # Index race: separate thread-owned connections, same DB, both pass readiness check.
    race_db = work / "index-race.sqlite"
    race_store = Store(race_db)
    race_store.ingest(first, "race")
    race_store.close()
    barrier2 = threading.Barrier(2)
    original_chunk = idx.chunk_turns
    race_results = []
    def synchronized_chunk(*args):
        barrier2.wait(timeout=10)
        return original_chunk(*args)
    def build_worker(n):
        own = Store(race_db)
        try:
            race_results.append({"worker": n, **capture(lambda: Index(own, FakeModels(), Config()).build("race", dense=False))})
        finally:
            own.close()
    with patch.object(idx, "chunk_turns", synchronized_chunk):
        threads = [threading.Thread(target=build_worker, args=(n,)) for n in range(2)]
        for t in threads: t.start()
        for t in threads: t.join(15)
    out["ING-08"] = {"workers": race_results}

    # Cached result version mismatch: Models snapshots lock once; fingerprint rereads it.
    lockroot = work / "lockroot"
    lockroot.mkdir()
    lockpath = lockroot / "models.lock.json"
    lock1 = {Config().embedding: "revision-A", Config().reranker: "revision-A"}
    lock2 = {Config().embedding: "revision-B", Config().reranker: "revision-B"}
    lockpath.write_text(json.dumps(lock1))
    with patch.object(cfg, "ROOT", lockroot), patch("decision_memory.models.device", return_value="cpu"):
        model = Models(Config())
        initial = Config().fingerprint
        lockpath.write_text(json.dumps(lock2))
        out["ING-09"] = {"model_snapshot": model.revisions, "current_lock": cfg.revisions(),
                         "fingerprint_changed_while_model_unchanged": Config().fingerprint != initial}

    # Allocation/load exceptions bypass the forward-only MPS fallback.
    mock = object.__new__(Models)
    mock.config, mock.device, mock.lock, mock._embedding = Config(), "mps", threading.RLock(), None
    def failing_load(*_args, **_kwargs):
        raise RuntimeError("MPS out of memory during model allocation")
    mock._load = failing_load
    out["ING-10"] = {"embed": capture(lambda: mock.embed(["Camera budget"])), "device_after_error": mock.device}

    # A caller can mutate cached records; the same Memory instance then serves the mutation.
    turn = {"role": "user", "content": "Camera approved."}
    records = memory.records(turn)
    records[0]["start"] = 99999
    out["ING-11"] = {"start_on_second_read": memory.records(turn)[0]["start"]}

    # Caller-supplied history list is silently reduced to IDs that happen to exist.
    out["ING-12"] = capture(lambda: Index(store, FakeModels(), Config()).build("dev", ["does-not-exist"], dense=False))

    # Raw vector BLOBs are fetched even for lexical candidates. Trace verifies SELECT shape.
    Index(store, FakeModels(), Config()).build("dev")
    queries = []
    store.db.set_trace_callback(queries.append)
    q = {"split": "dev", "history_id": "h1", "iso": "2023-06-01T00:00"}
    lexical, _ = Index(store, FakeModels(), Config()).candidates(q, False)
    store.db.set_trace_callback(None)
    out["ING-13"] = {"lexical_candidate_count": len(lexical),
                     "vector_select_in_lexical_mode": any("s.history_id,e.vector" in s for s in queries),
                     "vector_blob_bytes_in_eligible_rows": store.db.execute(
                         "SELECT sum(length(e.vector)) FROM sessions s JOIN chunks c ON s.content_hash=c.content_hash "
                         "JOIN embeddings e ON c.chunk_id=e.chunk_id WHERE split='dev' AND history_id='h1'").fetchone()[0]}

    # Deliberately invalid vector still accepted at the index boundary (producer simulated).
    class InvalidModels(FakeModels):
        key = "invalid-model"
        def embed(self, texts, query=False):
            return np.full((len(texts), 8), np.nan, dtype=np.float32)
    invalid = InvalidModels()
    badindex = Index(store, invalid, Config())
    badindex.build("dev")
    _, vecs = badindex.candidates(q, True)
    out["ING-14"] = {"nonfinite_vectors_accepted": not bool(np.isfinite(vecs).all())}
    out["ING-15"] = {"cue_examples": {s: cues(s) for s in ["Not approved.", "Unapproved budget.", "Approved yesterday, revoked today."]}}

    # Tar format has no uniqueness check at dataset-file level.
    empty_tar = work / "empty.tar.gz"
    with tarfile.open(empty_tar, "w:gz"):
        pass
    duplicate_tar = work / "duplicate.tar.gz"
    with tarfile.open(duplicate_tar, "w:gz") as archive:
        for folder, text in (("one", "First session"), ("two", "Second session")):
            raw = (json.dumps(history("tar-history", folder, text)) + "\n").encode()
            info = tarfile.TarInfo(folder + "/histories.jsonl")
            info.size = len(raw)
            archive.addfile(info, io.BytesIO(raw))
    out["ING-17"] = {"empty_archive": capture(lambda: store.ingest(empty_tar, "empty")),
                     "duplicate_files": capture(lambda: store.ingest(duplicate_tar, "twofiles"))}
    out["ING-17"]["retained_sessions"] = sorted(store.valid_sessions("twofiles", "tar-history"))

    class CountingModels(FakeModels):
        key = "counting-model"
        def __init__(self):
            self.calls = []
        def embed(self, texts, query=False):
            self.calls.extend(texts)
            return super().embed(texts, query)
    source = dataset(work / "repeated-text", [history("repeat", text="weather " * 2200)], [])
    store.ingest(source, "repeat")
    counter = CountingModels()
    build_report = Index(store, counter, Config()).build("repeat")
    out["ING-18"] = {"embedded_documents": len(counter.calls),
                     "distinct_embedded_texts": len(set(counter.calls)), "build_report": build_report}

    # Every replaced content revision remains stored after normal reingest/reindex.
    for revision in range(3):
        source = dataset(work / "revisions", [history("revisions", text=f"Camera revision {revision}.")], [])
        store.ingest(source, "revisions")
        Index(store, FakeModels(), Config()).build("revisions")
    out["ING-19"] = {"referenced_content_rows": store.db.execute("SELECT count(distinct content_hash) FROM sessions").fetchone()[0],
                     "all_content_rows": store.db.execute("SELECT count(*) FROM contents").fetchone()[0],
                     "orphan_content_rows": store.db.execute("SELECT count(*) FROM contents c WHERE NOT EXISTS "
                         "(SELECT 1 FROM sessions s WHERE s.content_hash=c.hash)").fetchone()[0]}

    store.close()
    return out


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="full-pipeline-ing-") as temp:
        results = run(Path(temp))
    here = Path(__file__).resolve().parent
    (here / "ing-probe-results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))
