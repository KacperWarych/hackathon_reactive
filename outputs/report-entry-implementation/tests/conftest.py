import io
import json
import re
import tarfile

import numpy as np
import pytest

from decision_memory.config import Config, digest
from decision_memory.index import Index
from decision_memory.store import Store, iso_date


class Tokenizer:
    def __call__(self, text, **kwargs):
        offsets = [m.span() for m in re.finditer(r"\S+\s*", text)]
        return {"offset_mapping": offsets, "input_ids": list(range(len(offsets)))}

    def encode(self, text, **kwargs):
        return text.split()


class FakeModels:
    """Deterministic test double, never used for production predictions."""
    tokenizer = Tokenizer()
    revisions = {Config().embedding: "test-revision"}
    key = "test-embedding"

    def embed(self, texts, query=False):
        words = ("camera", "lens", "budget", "approved", "radio", "resolved", "waiting", "other")
        vectors = np.array([[t.lower().count(w) + .01 for w in words] for t in texts], dtype=np.float32)
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

    def rerank(self, question, docs):
        return [float(len(set(question.lower().split()) & set(d.lower().split()))) for d in docs]


def put_session(store, hid, sid, text, date="2023/05/20 (Sat) 10:00", role="user", split="dev"):
    turns = [{"turn_id": "t_" + sid, "role": role, "content": text}]
    key = digest(turns)
    store.db.execute("INSERT OR IGNORE INTO contents VALUES(?,?)", (key, json.dumps(turns)))
    store.db.execute("INSERT OR REPLACE INTO sessions VALUES(?,?,?,?,?,?,?)", (split, hid, sid, date, iso_date(date), 0, key))
    store.db.commit()


def put_question(store, qid="q1", hid="h1", text="Which camera lens is approved?", split="dev", date="2023/06/01 (Thu) 10:00"):
    store.db.execute("INSERT INTO questions VALUES(?,?,?,?,?,?)", (split, qid, hid, text, date, iso_date(date)))
    store.db.commit()
    return store.questions(split, [qid])[0]


def archive(path, files):
    with tarfile.open(path, "w:gz") as tar:
        for name, records in files.items():
            data = "".join(json.dumps(r)+"\n" for r in records).encode()
            entry = tarfile.TarInfo("dev/" + name)
            entry.size = len(data)
            tar.addfile(entry, io.BytesIO(data))


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMORY_DATA_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def store(env):
    value = Store(env / "memory.sqlite")
    yield value
    value.close()


@pytest.fixture
def indexed(store):
    put_session(store, "h1", "s1", "The camera lens budget is waiting for approval.")
    put_session(store, "h1", "s2", "The camera lens is approved and the budget concern is resolved.", "2023/05/25 (Thu) 10:00")
    put_session(store, "h1", "future", "A different camera was approved.", "2023/07/01 (Sat) 10:00")
    put_session(store, "other", "s_other", "The camera lens costs 1000. Other person's purchase.")
    q = put_question(store)
    models = FakeModels()
    Index(store, models, Config()).build("dev")
    return q, models
