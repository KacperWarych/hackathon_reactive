import json

import pytest

from conftest import FakeModels, archive
from decision_memory.config import Config
from decision_memory.index import Index
from decision_memory.retrieval import Retriever


def dataset(path):
    (path / "public").mkdir(parents=True)
    (path / "gold").mkdir()
    records = {
        "histories.jsonl": [{"history_id": "campaign", "sessions": [{
            "session_id": "call", "date": "2026/09/01 (Tue) 05:40",
            "turns": [{"turn_id": "t1", "role": "user", "content": "Cena karnetu jest za wysoka."}]}]}],
        "questions.jsonl": [{"question_id": "q1", "history_id": "campaign",
            "question": "Czy cena karnetu jest za wysoka?", "question_date": "2026/10/31 (Sat) 00:00"}],
        "gold.jsonl": [{"question_id": "q1", "answer": "EVALUATION_ONLY"}],
    }
    for name, rows in records.items():
        folder = "gold" if name == "gold.jsonl" else "public"
        (path / folder / name).write_text("".join(json.dumps(r) + "\n" for r in rows))
    (path / "gold/calls_gold.jsonl").write_text("not an input")
    return records


def test_directory_matches_archive_and_retrieves_polish(store, env):
    source = env / "dataset"
    rows = dataset(source)
    packed = env / "dataset.tar.gz"
    archive(packed, rows)
    expected = {"histories": 1, "sessions": 1, "questions": 1}
    assert store.ingest(source, "salesgen") == expected
    assert store.ingest(source, "salesgen") == expected
    assert store.ingest(packed, "archived") == expected
    assert store.sessions("salesgen", "campaign")[0]["turns"] == store.sessions("archived", "campaign")[0]["turns"]
    assert len(store.sessions("salesgen", "campaign")) == 1
    assert "EVALUATION_ONLY" not in str(list(store.db.execute("SELECT * FROM contents")))
    assert "EVALUATION_ONLY" in (env / "evaluation/gold-salesgen.jsonl").read_text()
    models = FakeModels()
    Index(store, models, Config()).build("salesgen", dense=False)
    result = Retriever(store, models).retrieve(store.questions("salesgen")[0], "bm25")
    assert result["evidence"][0]["id"] == "call"
    assert "Cena karnetu" in result["evidence"][0]["text"]


def test_public_only_and_history_filter(store, env):
    source = env / "dataset"
    dataset(source)
    assert store.ingest(source / "public", "public")["questions"] == 1
    assert not (env / "evaluation/gold-public.jsonl").exists()
    assert store.ingest(source, "filtered", {"other"}) == {"histories": 0, "sessions": 0, "questions": 0}


def test_missing_input_and_unsafe_split_fail_before_ingestion(store, env):
    source = env / "dataset"
    dataset(source)
    with pytest.raises(ValueError, match="Split names"):
        store.ingest(source, "../escape")
    (source / "public/questions.jsonl").unlink()
    with pytest.raises(FileNotFoundError, match="questions.jsonl"):
        store.ingest(source, "missing")
    assert store.stats() == []
