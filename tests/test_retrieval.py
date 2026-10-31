from dataclasses import replace

import pytest

from conftest import FakeModels, Tokenizer, archive, put_question, put_session
from decision_memory.chunks import chunk_turns
from decision_memory.config import Config
from decision_memory.index import Index
from decision_memory.retrieval import Retriever, distinct, fuse, message_size, terms
from decision_memory.store import iso_date


def test_dates_are_parsed_not_guessed():
    assert iso_date("2023/05/20 (Sat) 02:21") == "2023-05-20T02:21"
    with pytest.raises(ValueError):
        iso_date("yesterday")


@pytest.mark.parametrize("mode", ["bm25", "dense", "hybrid", "rerank", "full"])
def test_history_and_time_isolation(indexed, store, mode):
    q, models = indexed
    result = Retriever(store, models).retrieve(q, mode)
    assert {x["id"] for x in result["evidence"]} == {"s1", "s2"}
    assert all(x["session_id"] not in {"future", "s_other"} for x in result["trace"]["candidates"])
    assert result["trace"]["message_chars"] <= 16000
    assert "user:" in result["evidence"][0]["text"]
    if mode == "full":
        assert not result["trace"]["expansion_queries"]
        assert result["trace"]["expansion_reason"] is None


def test_session_dates_are_history_specific(store):
    put_session(store, "a", "shared", "camera lens", "2023/05/01 (Mon) 10:00")
    put_session(store, "b", "shared", "camera lens", "2023/07/01 (Sat) 10:00")
    a = put_question(store, qid="a", hid="a")
    b = put_question(store, qid="b", hid="b")
    models = FakeModels()
    index = Index(store, models, Config())
    index.build("dev")
    assert len(index.candidates(a, True)[0]) == 1
    assert len(index.candidates(b, True)[0]) == 0
    assert store.db.execute("SELECT count(*) FROM embeddings").fetchone()[0] == 1


def test_index_is_idempotent(indexed, store):
    _, models = indexed
    before = store.db.execute("SELECT count(*) FROM embeddings").fetchone()[0]
    report = Index(store, models, Config()).build("dev")
    assert report["new_vectors"] == 0
    assert before == store.db.execute("SELECT count(*) FROM embeddings").fetchone()[0]


def test_missing_index_fails_instead_of_silently_skipping(store):
    put_session(store, "h1", "s1", "camera lens")
    q = put_question(store)
    with pytest.raises(RuntimeError, match="unindexed"):
        Retriever(store, FakeModels()).retrieve(q, "bm25")


def test_chunks_cover_long_turn_with_overlap_and_roles():
    turns = [{"turn_id": "t1", "role": "user", "content": " ".join(f"word{i}" for i in range(1500))},
             {"turn_id": "t2", "role": "assistant", "content": "That is a proposed option, not a purchase."}]
    rows = chunk_turns(turns, Tokenizer(), Config())
    assert len(rows) > 2
    assert max(r["tokens"] for r in rows) <= 600
    assert all(a["end"] >= b["start"] for a, b in zip(rows, rows[1:]))
    assert "word1499" in rows[-1]["text"]
    assert "assistant:" in rows[-1]["text"]
    assert "user (continued):" in rows[1]["text"]


def test_budget_includes_question_dates_labels_and_instructions(indexed, store):
    q, models = indexed
    config = replace(Config(), evidence_chars=100, max_message_chars=1300)
    result = Retriever(store, models, config).retrieve(q, "bm25")
    assert sum(len(e["text"]) for e in result["evidence"]) <= 100
    assert message_size(q, result["evidence"]) <= 1300


def test_product_codes_and_fusion():
    assert "rf-2200" in terms("Panasonic RF-2200 at 1.5 volts")
    assert "r-77" not in terms("Panasonic RF-2200")
    ranking, scores = fuse([[1, 2], [2, 3]])
    assert ranking[0] == 2 and scores[2] > scores[1]


def test_overlap_deduplication_preserves_distinct_sessions():
    rows = [{"session_id": "a", "start": 0, "end": 100},
            {"session_id": "a", "start": 10, "end": 90},
            {"session_id": "b", "start": 10, "end": 90}]
    assert distinct([0, 1, 2], rows) == [0, 2]


def test_archive_ingest_idempotent_and_gold_separate(store, env):
    path = env / "dev.tar.gz"
    archive(path, {"histories.jsonl": [{"history_id": "h1", "sessions": [{"session_id": "s1", "date": "2023/05/20 (Sat) 10:00", "turns": [{"turn_id": "t1", "role": "user", "content": "My camera lens."}]}]}],
                   "questions.jsonl": [{"question_id": "q1", "history_id": "h1", "question": "Which lens?", "question_date": "2023/06/01 (Thu) 10:00"}],
                   "gold.jsonl": [{"question_id": "q1", "answer": "secret answer"}]})
    store.ingest(path, "dev"); store.ingest(path, "dev")
    assert store.stats()[0]["sessions"] == 1
    assert "secret answer" not in str(store.questions("dev"))
    assert (env / "evaluation" / "gold-dev.jsonl").exists()


def test_expansion_keeps_original_candidates_eligible(store):
    for n in range(60):
        put_session(store, "h1", f"s{n}", f"Camera lens RF-{n} is approved. Updated budget {n}.")
    q = put_question(store)
    models = FakeModels()
    Index(store, models, Config()).build("dev")
    retriever = Retriever(store, models)
    original = retriever.retrieve(q, "rerank")
    expanded = retriever.retrieve(q, "full")
    original_ids = {c["chunk_id"] for c in original["trace"]["candidates"]}
    expanded_ids = {c["chunk_id"] for c in expanded["trace"]["candidates"]}
    assert len(original_ids) == 40
    assert original_ids <= expanded_ids
    assert len(expanded_ids) <= 80
    assert expanded["trace"]["searches"][0]["query"] == q["question"]
    assert set(expanded["trace"]["searches"][0]["rankings"]) == {"bm25", "dense"}


def test_overlap_deduplication_retains_unique_tail_and_changed_source():
    rows = [{"session_id": "a", "content_hash": "original", "date": "2023-05-01", "start": 0, "end": 100},
            {"session_id": "a", "content_hash": "original", "date": "2023-05-01", "start": 10, "end": 110},
            {"session_id": "a", "content_hash": "edited", "date": "2023-05-01", "start": 0, "end": 100}]
    assert distinct([0, 1, 2], rows) == [0, 1, 2]
