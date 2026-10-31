import json
from contextlib import nullcontext

import pytest

from conftest import put_question
from decision_memory.config import Config, atomic_json
from decision_memory.reactor import agent_lock, checked_result, export_predictions, result_path, run_questions
from decision_memory.retrieval import Retriever


class Adapter:
    agent_key = "fake-agent"

    def __init__(self, fail=False):
        self.calls = []; self.fail = fail

    def lock(self):
        return nullcontext()

    def call(self, *args):
        self.calls.append(args)
        if args[0] == "--new-history":
            return {"status": "history", "history_id": "reactor-h1"}
        if self.fail:
            return {"status": "timeout"}
        return {"status": "answered", "answer": "Approved [E1].", "citations": [{"label": "E1", "id": "s1"}], "abstained": False}


def test_agent_lock_is_exclusive():
    with agent_lock("https://test.invalid", "test-agent"):
        with pytest.raises(RuntimeError, match="in use"):
            with agent_lock("https://test.invalid", "test-agent"):
                pass


def test_resume_does_not_repeat_completed_answers(indexed, store, env):
    q, models = indexed
    q2 = put_question(store, qid="q2")
    adapter = Adapter()
    retriever = Retriever(store, models)
    run_questions(store, retriever, [q2, q], "test-run", "bm25", adapter=adapter)
    assert sum(c[0] == "--new-history" for c in adapter.calls) == 1
    assert len(adapter.calls) == 3
    run_questions(store, retriever, [q, q2], "test-run", "bm25", adapter=adapter)
    assert len(adapter.calls) == 3
    out = env / "predictions.jsonl"
    assert export_predictions(store, "test-run", out)["written"] == 2
    assert len({json.loads(line)["question_id"] for line in out.read_text().splitlines()}) == 2


def test_timeout_remains_incomplete_and_is_not_blindly_retried(indexed, store, env):
    q, models = indexed
    adapter = Adapter(fail=True)
    retriever = Retriever(store, models)
    with pytest.raises(RuntimeError, match="stopped"):
        run_questions(store, retriever, [q], "failed", "bm25", adapter=adapter)
    calls = len(adapter.calls)
    with pytest.raises(RuntimeError, match="needs review"):
        run_questions(store, retriever, [q], "failed", "bm25", adapter=adapter)
    assert len(adapter.calls) == calls
    with pytest.raises(RuntimeError, match="Export blocked"):
        export_predictions(store, "failed", env/"predictions.jsonl")
    assert not (env/"predictions.jsonl").exists()


def test_pending_request_requires_explicit_recovery(indexed, store, env):
    q, models = indexed
    retriever = Retriever(store, models)
    path = result_path(env/"runs"/"crashed", q["question_id"])
    atomic_json(path, {"result": {"status": "pending"}})
    with pytest.raises(RuntimeError, match="needs review"):
        run_questions(store, retriever, [q], "crashed", "bm25", adapter=Adapter())


def test_foreign_or_unknown_citations_are_rejected(indexed, store):
    q, _ = indexed
    response = {"status": "answered", "answer": "Other [E1]", "citations": [{"id": "s_other"}]}
    assert checked_result(response, q, [{"id":"s1"}], store)["status"] == "invalid"
    response = {"status": "answered", "answer": "Other", "citations": []}
    assert checked_result(response, q, [], store)["status"] == "invalid"


def test_abstention_is_a_completed_model_outcome(indexed, store):
    q, _ = indexed
    response = {"status":"answered", "answer":"INSUFFICIENT_EVIDENCE", "abstained":True, "citations":[]}
    assert checked_result(response, q, [], store)["status"] == "answered"


def test_test_export_requires_entire_official_set(indexed, store, env):
    q, _ = indexed
    put_question(store, qid="test-q", split="test")
    atomic_json(env/"runs"/"partial"/"run.json", {"split":"test", "question_ids":["test-q"]})
    with pytest.raises(RuntimeError):
        export_predictions(store, "partial", env/"submission.jsonl")


def test_history_change_requires_review_and_resets_local_state(indexed, store, env):
    q, models = indexed

    class ChangedHistory(Adapter):
        def call(self, *args):
            if args[0] == "--new-history":
                return super().call(*args)
            return {"status": "error", "code": "history_changed"}

    with pytest.raises(RuntimeError, match="stopped"):
        run_questions(store, Retriever(store, models), [q], "changed", "bm25", adapter=ChangedHistory())
    assert json.loads((env/"agents"/"fake-agent.json").read_text()) == {}
    record = json.loads(result_path(env/"runs"/"changed", q["question_id"]).read_text())
    assert record["result"]["status"] == "error"


def test_answer_evaluation_separates_abstention_errors(indexed, store, env):
    from decision_memory.evaluation import evaluate_answers
    q, _ = indexed
    second = put_question(store, qid="q2")
    annotations = [
        {"question_id": q["question_id"], "question_type": "single-session-user", "abstain": True, "evidence": []},
        {"question_id": second["question_id"], "question_type": "single-session-user", "abstain": False, "answer": "lens", "evidence": ["s1"]}]
    (env/"evaluation").mkdir()
    (env/"evaluation"/"gold-dev.jsonl").write_text("\n".join(json.dumps(r) for r in annotations))
    run = env/"runs"/"scoring"
    atomic_json(run/"run.json", {"split": "dev", "question_ids": [q["question_id"], second["question_id"]]})
    for question, abstained in ((q, False), (second, True)):
        atomic_json(result_path(run, question["question_id"]), {"result": {
            "status": "answered", "answer": "lens", "abstained": abstained, "citations": [], "latency_s": 2.0}})
    report = evaluate_answers(store, "scoring")
    assert report["judgments"] == {"missed_abstention": 1, "unnecessary_abstention": 1}
    assert report["abstention_precision"] == 0 and report["abstention_recall"] == 0


def test_partial_ingestion_never_claims_submission_ready(store, env):
    q = put_question(store, qid="test-q", split="test")
    run = env/"runs"/"partial-ingest"
    atomic_json(run/"run.json", {"split": "test", "question_ids": [q["question_id"]]})
    atomic_json(result_path(run, q["question_id"]), {"retrieval": {"evidence": []}, "result": {
        "status": "answered", "abstained": True, "answer": "INSUFFICIENT_EVIDENCE", "citations": []}})
    report = export_predictions(store, "partial-ingest", env/"partial.jsonl", allow_partial=True)
    assert report["written"] == 1 and not report["submission_ready"]


def test_all_official_questions_required_for_submission_ready(store, env):
    questions = [put_question(store, qid=f"test-q{i}", split="test") for i in range(146)]
    run = env/"runs"/"complete-test"
    atomic_json(run/"run.json", {"split": "test", "question_ids": [q["question_id"] for q in questions]})
    for q in questions:
        atomic_json(result_path(run, q["question_id"]), {"retrieval": {"evidence": []}, "result": {
            "status": "answered", "abstained": True, "answer": "INSUFFICIENT_EVIDENCE", "citations": []}})
    report = export_predictions(store, "complete-test", env/"test.jsonl")
    assert report["written"] == 146 and report["submission_ready"]


def test_uncited_answer_gets_one_audited_corrective_followup(indexed, store, env):
    q, models = indexed

    class UncitedFirst(Adapter):
        def call(self, *args):
            result = super().call(*args)
            if len(self.calls) == 2:
                return {"status": "answered", "answer": "Approved.", "citations": [], "abstained": False}
            return result

    adapter = UncitedFirst()
    run_questions(store, Retriever(store, models), [q], "citation-fix", "bm25", adapter=adapter)
    record = json.loads(result_path(env/"runs"/"citation-fix", q["question_id"]).read_text())
    assert [r["kind"] for r in record["requests"]] == ["initial", "citation_repair"]
    assert record["requests"][0]["result"]["answer"] == "Approved."
    assert record["result"]["citations"][0]["id"] == "s1"
    assert len(adapter.calls) == 3
    assert adapter.calls[1][1] == adapter.calls[2][1]  # same Reactor history
    assert "IN THE FINAL ANSWER LINE" in adapter.calls[2][3]


@pytest.mark.parametrize("repair_status", ["answered", "timeout"])
def test_citation_repair_is_bounded_and_uncertainty_still_stops(indexed, store, env, repair_status):
    q, models = indexed

    class Uncited(Adapter):
        def call(self, *args):
            result = super().call(*args)
            if len(self.calls) == 2 or args[0] != "--new-history" and repair_status == "answered":
                return {"status": "answered", "answer": "Approved.", "citations": [], "abstained": False}
            if args[0] != "--new-history":
                return {"status": "timeout"}
            return result

    adapter = Uncited()
    retriever = Retriever(store, models)
    with pytest.raises(RuntimeError, match="stopped"):
        run_questions(store, retriever, [q], "bounded-fix", "bm25", adapter=adapter)
    assert len(adapter.calls) == 3
    with pytest.raises(RuntimeError, match="needs review"):
        run_questions(store, retriever, [q], "bounded-fix", "bm25", adapter=adapter)
    assert len(adapter.calls) == 3
