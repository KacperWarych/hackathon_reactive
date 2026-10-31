import copy
import json
from contextlib import nullcontext
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import put_session
from decision_memory.config import Config, atomic_json
from decision_memory.decision import SECTIONS
from decision_memory.index import Index
from decision_memory.investigations import (
    InvestigationError,
    Investigations,
    revision_report,
)
from decision_memory.retrieval import Retriever
from decision_memory.vendor.reactor_client import build_message


class Adapter:
    agent_key = "investigation-test-agent"

    def __init__(self):
        self.calls = []
        self.fail = None
        self.uncited = False

    def lock(self):
        return nullcontext()

    def call(self, *args):
        self.calls.append(args)
        if args[0] == "--new-history":
            return {"status": "history", "history_id": f"memory-{len(self.calls)}"}
        field = args[args.index("--question-id") + 1].split("_")[-2]
        if self.fail == field:
            return {"status": "timeout"}
        text = args[args.index("--question") + 1]
        evidence = (
            json.loads(Path(args[args.index("--evidence") + 1]).read_text()) if "--evidence" in args else []
        )
        if not evidence:
            return {
                "status": "answered",
                "answer": "INSUFFICIENT_EVIDENCE",
                "abstained": True,
                "citations": [],
            }
        if self.uncited and "IN THE FINAL ANSWER LINE" not in text:
            return {"status": "answered", "answer": "Uncited", "citations": []}
        if field == "decision":
            obj = {s: [] for s in SECTIONS}
            obj["concerns"] = [{"text": f"Concern on turn {len(self.calls)}", "sources": ["E1"]}]
            answer = json.dumps(obj) + " [E1]"
        else:
            answer = f"Answer on turn {len(self.calls)} [E1]"
        return {
            "status": "answered",
            "answer": answer,
            "citations": [{"label": "E1", "id": evidence[0]["id"]}],
        }


@pytest.fixture
def setup(indexed, store):
    question, models = indexed
    retriever = Retriever(store, models)
    report = {
        "id": "old-report",
        "created_at": "31 Oct 2026",
        "retrieval": retriever.retrieve(question, "bm25"),
        "answer_record": None,
        "decision_record": None,
        "evaluation": None,
    }
    adapter = Adapter()
    return report, Investigations(store, retriever, adapter=adapter), adapter


def test_adopts_saved_reports_without_live_calls_and_keeps_seed(setup):
    report, service, adapter = setup
    document = service.document(report)
    assert service.document(report) == document
    assert document["revisions"][0]["retrieval"] == report["retrieval"]
    assert not adapter.calls


def test_answer_history_and_followups_share_memory_but_keep_distinct_revisions(setup):
    report, service, adapter = setup
    first = service.revise(report)
    first_document = service.document(first)
    second = service.revise(first, "Focus on the budget and explain the remaining concern.")
    doc = service.document(second)
    assert first["investigation_id"] == second["investigation_id"]
    assert first["revision_id"] != second["revision_id"]
    assert first["answer_record"]["reactor_history"] == second["decision_record"]["reactor_history"]
    assert sum(c[0] == "--new-history" for c in adapter.calls) == 1
    assert len(adapter.calls) == 5
    assert doc["revisions"][1] == first_document["revisions"][1]
    assert doc["revisions"][2]["parent_id"] == first["revision_id"]
    assert "Focus on the budget" in doc["revisions"][2]["retrieval"]["trace"]["investigation_query"]
    assert doc["revisions"][2]["changes"]["answer_changed"]


def test_service_reload_continues_persisted_memory(setup, store):
    report, service, adapter = setup
    first = service.revise(report)
    resumed = Investigations(store, service.retriever, adapter=adapter)
    resumed.revise(first, "Why?")
    assert sum(c[0] == "--new-history" for c in adapter.calls) == 1


def test_new_conversation_is_retrieved_and_date_backwards_resets_memory(setup, store):
    report, service, adapter = setup
    first = service.revise(report)
    put_session(
        store,
        "h1",
        "new-update",
        "The camera budget is approved and procurement is still waiting.",
        "2023-06-02 10:00",
    )
    Index(store, service.retriever.models, service.config).build("dev")
    service.retriever._cache = None
    second = service.revise(first, "What is still waiting?", "2023-06-03 10:00")
    assert "new-update" in {e["id"] for e in second["retrieval"]["evidence"]}
    assert sum(c[0] == "--new-history" for c in adapter.calls) == 1
    third = service.revise(second, question_date="2023-05-21 10:00")
    assert sum(c[0] == "--new-history" for c in adapter.calls) == 2
    assert "new-update" not in {e["id"] for e in third["retrieval"]["evidence"]}
    assert "s2" not in {e["id"] for e in third["retrieval"]["evidence"]}


def test_changed_original_source_resets_memory(setup, store):
    report, service, adapter = setup
    first = service.revise(report)
    put_session(
        store,
        "h1",
        "s1",
        "The camera budget is still waiting for approval after correction.",
    )
    Index(store, service.retriever.models, service.config).build("dev")
    service.retriever._cache = None
    service.revise(first)
    assert sum(c[0] == "--new-history" for c in adapter.calls) == 2


def test_switching_investigations_rebuilds_original_and_followup_context(setup):
    report, service, adapter = setup
    first = service.revise(report, "Focus on the budget")
    other = {**report, "id": "another-report"}
    service.revise(other)
    service.revise(first, "Explain why")
    assert sum(c[0] == "--new-history" for c in adapter.calls) == 3
    body = adapter.calls[-1][adapter.calls[-1].index("--question") + 1]
    assert report["retrieval"]["question"]["question"] in body
    assert "Focus on the budget" in body and "Explain why" in body
    assert "Earlier answers are interpretations, not evidence" in body
    assert "Earlier report draft" in body
    assert first["answer_record"]["result"]["answer"].replace("[E1]", "") in body


def test_other_agent_client_or_benchmark_state_forces_reconstruction(setup, env):
    report, service, adapter = setup
    first = service.revise(report)
    atomic_json(
        env / "agents" / (adapter.agent_key + ".json"),
        {"key": ["benchmark", "dev", "h1"], "reactor_history": "other"},
    )
    service.revise(first)
    assert sum(c[0] == "--new-history" for c in adapter.calls) == 2


def test_partial_failure_preserves_previous_pair_and_requires_explicit_recovery(setup):
    report, service, adapter = setup
    first = service.revise(report)
    adapter.fail = "decision"
    with pytest.raises(InvestigationError, match="previous version is intact"):
        service.revise(first, "Focus on the budget")
    doc = service.document(first)
    assert doc["current_revision"] == first["revision_id"]
    assert doc["revisions"][-1]["answer_record"]["result"]["status"] == "answered"
    assert doc["revisions"][-1]["status"] == "failed"
    calls = len(adapter.calls)
    with pytest.raises(InvestigationError, match="Restart memory"):
        service.revise(first)
    assert len(adapter.calls) == calls
    adapter.fail = None
    recovered = service.revise(first, "Focus on the budget", recover=True)
    assert recovered["revision_number"] == 3
    assert sum(c[0] == "--new-history" for c in adapter.calls) == 2


def test_stale_report_cannot_overwrite_a_newer_revision(setup):
    report, service, adapter = setup
    first = service.revise(report)
    service.revise(first, "Why?")
    calls = len(adapter.calls)
    with pytest.raises(InvestigationError, match="older version"):
        service.revise(first, "Another prompt")
    assert len(adapter.calls) == calls


def test_foreign_and_future_evidence_rejected_before_any_reactor_call(setup):
    report, service, adapter = setup
    evidence = copy.deepcopy(report["retrieval"])
    evidence["evidence"][0]["id"] = "future"

    class BadRetriever:
        def retrieve(self, *args):
            return evidence

    service.retriever = BadRetriever()
    with pytest.raises(ValueError, match="time boundary"):
        service.revise(report)
    assert not adapter.calls


def test_one_citation_repair_per_section_shares_the_active_memory(setup):
    report, service, adapter = setup
    adapter.uncited = True
    revised = service.revise(report)
    doc = service.document(revised)
    assert [r["kind"] for r in doc["revisions"][-1]["requests"]] == [
        "initial",
        "citation_repair",
        "initial",
        "citation_repair",
    ]
    assert sum(c[0] == "--new-history" for c in adapter.calls) == 1


def test_both_sections_use_same_evidence_and_complete_request_budget(setup):
    report, service, adapter = setup
    service.config = replace(Config(), max_message_chars=3500)
    revised = service.revise(report)
    first, second = revised["answer_record"], revised["decision_record"]
    assert first["retrieval"]["evidence"] == second["retrieval"]["evidence"]
    for call in adapter.calls:
        if call[0] == "--new-history":
            continue
        text = call[call.index("--question") + 1]
        evidence = (
            json.loads(Path(call[call.index("--evidence") + 1]).read_text()) if "--evidence" in call else []
        )
        assert len(build_message(text, evidence, "00000000", "2023-06-01 10:00")) <= 3500


def test_invalid_decision_structure_does_not_publish_revision(setup):
    report, service, adapter = setup
    original = adapter.call

    def invalid(*args):
        result = original(*args)
        if "--question-id" in args and "decision_record" in args[args.index("--question-id") + 1]:
            result["answer"] = "Unstructured interpretation [E1]"
        return result

    adapter.call = invalid
    with pytest.raises(InvestigationError, match="structured"):
        service.revise(report)
    doc = service.document(report)
    assert doc["current_revision"] == doc["revisions"][0]["id"]


def test_unanswerable_revision_is_completed_abstention(setup):
    report, service, adapter = setup
    revised = service.revise(report, question_date="2023-01-01 00:00")
    assert revised["answer_record"]["result"]["abstained"]
    assert revised["decision_record"]["result"]["abstained"]


def test_overlong_context_and_path_traversal_are_rejected(setup):
    report, service, adapter = setup
    with pytest.raises(ValueError, match="2,000"):
        service.revise(report, "x" * 2001)
    with pytest.raises(ValueError, match="identity"):
        service.document({**report, "investigation_id": "../../other"})
    assert not adapter.calls


def test_two_writers_cannot_generate_for_same_investigation(setup):
    report, service, adapter = setup
    with service._lock(report):
        with pytest.raises(InvestigationError, match="already being revised"):
            service.revise(report)
    assert not adapter.calls


def test_selected_older_version_remains_readable(setup):
    report, service, adapter = setup
    revised = service.revise(report)
    doc = service.document(revised)
    seed = revision_report(revised, doc, doc["revisions"][0])
    assert seed["revision_number"] == 0
    assert seed["answer_record"] is None
    assert seed["retrieval"] == report["retrieval"]


def test_decision_only_reuses_saved_answer_and_evidence_without_retrieving(setup):
    report, service, adapter = setup
    report = service.revise(report)
    calls = len(adapter.calls)
    def unexpected(*args):
        raise AssertionError("Decision-only build must reuse the saved evidence")
    service.retriever.retrieve = unexpected
    rebuilt = service.revise(report, decision_only=True)
    assert len(adapter.calls) == calls + 1
    assert rebuilt["answer_record"] == report["answer_record"]
    assert rebuilt["retrieval"]["evidence"] == report["retrieval"]["evidence"]
    assert rebuilt["decision_record"] != report["decision_record"]


@pytest.mark.parametrize("persistent", [False, True])
def test_malformed_decision_has_one_audited_repair(setup, persistent):
    report, service, adapter = setup
    original = adapter.call
    failures = []
    def call(*args):
        result = original(*args)
        if "--question-id" in args and args[args.index("--question-id") + 1].endswith("decision_record"):
            if persistent or not failures:
                failures.append(True)
                result["answer"] = '{"goals": [{"text": \'invalid JSON\', "sources": ["E1"]}]}'
        return result
    adapter.call = call
    if persistent:
        with pytest.raises(InvestigationError, match="parsed"):
            service.revise(report)
    else:
        service.revise(report)
    revision = service.document(report)["revisions"][-1]
    assert [q["kind"] for q in revision["requests"]] == ["initial", "initial", "decision_repair"]
    assert revision["status"] == ("failed" if persistent else "complete")
    assert len(adapter.calls) == 4
