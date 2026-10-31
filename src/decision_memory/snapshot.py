"""One identity for the complete eligible source population of a question."""
from .config import digest


def eligible_fingerprint(store, question):
    sources = sorted(
        (s["session_id"], s["iso"], s["content_hash"])
        for s in store.sessions(question["split"], question["history_id"])
        if s["iso"] <= question["iso"]
    )
    return digest(sources)


def is_current(store, retrieval):
    question = retrieval["question"]
    return question.get("history_revision") == eligible_fingerprint(store, question)
