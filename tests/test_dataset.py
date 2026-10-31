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


def write_records(source, records):
    for name, rows in records.items():
        folder = "gold" if name == "gold.jsonl" else "public"
        (source / folder / name).write_text("".join(json.dumps(row) + "\n" for row in rows))


@pytest.mark.parametrize("defect", ["missing_id", "duplicate_id", "role", "date", "reference"])
def test_late_validation_failure_preserves_database_and_gold(store, env, defect):
    from conftest import Tokenizer
    from decision_memory.memory import Memory

    source = env / "dataset"
    records = dataset(source)
    store.ingest(source, "dev")
    before = store.sessions("dev", "campaign")
    questions = store.questions("dev")
    gold_path = env / "evaluation/gold-dev.jsonl"
    gold = gold_path.read_bytes()
    records["questions.jsonl"][0]["question"] = "Must not be committed"
    session = records["histories.jsonl"][0]["sessions"][0]
    session["turns"][0]["content"] = "Must not be committed either"
    if defect == "missing_id":
        session["turns"].append({"role": "user", "content": "Missing ID"})
    elif defect == "duplicate_id":
        session["turns"].append(dict(session["turns"][0]))
    elif defect == "role":
        session["turns"][0]["role"] = "system"
    elif defect == "date":
        records["questions.jsonl"][0]["question_date"] = "2026-99-99"
    else:
        records["questions.jsonl"][0]["history_id"] = "missing"
    write_records(source, records)
    with pytest.raises(ValueError):
        store.ingest(source, "dev")
    Memory(store, Tokenizer())  # executescript used to commit failed-import leftovers
    assert store.sessions("dev", "campaign") == before
    assert store.questions("dev") == questions
    assert gold_path.read_bytes() == gold
    assert not store.db.in_transaction


def test_missing_turn_id_has_actionable_error(store, env):
    source = env / "dataset"
    records = dataset(source)
    del records["histories.jsonl"][0]["sessions"][0]["turns"][0]["turn_id"]
    write_records(source, records)
    with pytest.raises(ValueError, match="turn_id in session call"):
        store.ingest(source, "dev")
    assert store.stats() == []


def test_sql_failure_rolls_back_all_rows_and_gold(store, env):
    from conftest import Tokenizer
    from decision_memory.memory import Memory

    source = env / "dataset"
    dataset(source)
    store.db.execute("CREATE TRIGGER reject_questions BEFORE INSERT ON questions BEGIN SELECT RAISE(ABORT, 'test failure'); END")
    with pytest.raises(Exception, match="test failure"):
        store.ingest(source, "fresh")
    Memory(store, Tokenizer())
    assert store.stats() == []
    assert store.questions("fresh") == []
    assert store.db.execute("SELECT count(*) FROM contents").fetchone()[0] == 0
    assert not (env / "evaluation/gold-fresh.jsonl").exists()
    assert not list((env / "evaluation").iterdir())


def test_gold_publication_failure_rolls_back_sql(store, env, monkeypatch):
    from pathlib import Path

    source = env / "dataset"
    dataset(source)
    def fail_replace(self, target):
        raise OSError("simulated publication failure")
    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError, match="publication failure"):
        store.ingest(source, "fresh")
    assert store.stats() == []
    assert store.questions("fresh") == []
    assert not list((env / "evaluation").iterdir())


def test_changed_gold_requires_fresh_split(store, env):
    source = env / "dataset"
    records = dataset(source)
    store.ingest(source, "dev")
    before = (env / "evaluation/gold-dev.jsonl").read_bytes()
    records["gold.jsonl"][0]["answer"] = "Different gold"
    write_records(source, records)
    with pytest.raises(ValueError, match="fresh split"):
        store.ingest(source, "dev")
    assert (env / "evaluation/gold-dev.jsonl").read_bytes() == before
    assert store.ingest(source, "fresh")["questions"] == 1


def test_archive_order_and_late_malformed_json_are_atomic(store, env):
    import io
    import tarfile

    source = env / "bad.tar.gz"
    records = dataset(env / "dataset")
    with tarfile.open(source, "w:gz") as tar:
        for name in ("gold.jsonl", "questions.jsonl", "histories.jsonl"):
            data = "".join(json.dumps(r) + "\n" for r in records[name]).encode()
            if name == "histories.jsonl":
                data += b'{"broken":\n'
            member = tarfile.TarInfo(name)
            member.size = len(data)
            tar.addfile(member, io.BytesIO(data))
    with pytest.raises(ValueError, match="histories.jsonl line 2"):
        store.ingest(source, "fresh")
    assert store.stats() == []
    assert store.questions("fresh") == []
    assert not (env / "evaluation/gold-fresh.jsonl").exists()


def test_commit_failure_removes_already_published_fresh_gold(store, env):
    import sqlite3

    source = env / "dataset"
    dataset(source)
    store.db.execute("PRAGMA foreign_keys=ON")
    store.db.executescript("""
        CREATE TABLE commit_parent (id INTEGER PRIMARY KEY);
        CREATE TABLE commit_child (parent_id INTEGER REFERENCES commit_parent(id) DEFERRABLE INITIALLY DEFERRED);
        CREATE TRIGGER deferred_failure AFTER INSERT ON questions
        BEGIN INSERT INTO commit_child VALUES(1); END;
    """)
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        store.ingest(source, "fresh")
    assert store.stats() == []
    assert store.questions("fresh") == []
    assert not store.db.in_transaction
    assert not (env / "evaluation/gold-fresh.jsonl").exists()
    assert not list((env / "evaluation").iterdir())


def test_fresh_split_not_visible_until_gold_is_published(store, env, monkeypatch):
    from pathlib import Path
    from decision_memory.store import Store

    source = env / "dataset"
    dataset(source)
    replace = Path.replace
    observed = []
    def inspect_publication(self, target):
        result = replace(self, target)
        reader = Store(store.path)
        try:
            observed.append((target.exists(), reader.stats(), reader.questions("fresh")))
        finally:
            reader.close()
        return result
    monkeypatch.setattr(Path, "replace", inspect_publication)
    store.ingest(source, "fresh")
    assert observed == [(True, [], [])]
    assert store.stats()[0]["split"] == "fresh"
