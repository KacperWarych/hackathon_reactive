import json

from decision_memory.decision import SECTIONS, validate_decision
from decision_memory.evaluation import evidence_metrics


def report(resolution):
    obj = {key: [] for key in SECTIONS}
    obj["resolutions"] = [resolution]
    return json.dumps(obj) + " [E1]"


def test_assistant_suggestion_cannot_supply_resolution_quote():
    answer = report({"text":"Integration resolved", "sources":["E1"], "confirmation_quote":"Try this integration workaround."})
    evidence = [{"text":"user: Integration is blocking us.\nassistant: Try this integration workaround."}]
    assert validate_decision(answer, evidence)[0] is None


def test_resolution_requires_traceable_user_confirmation():
    quote = "We tested it and the integration concern is resolved."
    answer = report({"text":"Integration resolved", "sources":["E1"], "confirmation_quote":quote})
    assert validate_decision(answer, [{"text":"user: "+quote}])[1] is None


def test_hypothetical_user_quote_is_not_rendered_as_resolution():
    quote = "If this workaround works, the concern could be resolved."
    answer = report({"text":"Integration resolved", "sources":["E1"], "confirmation_quote":quote})
    assert validate_decision(answer, [{"text":"user: "+quote}])[0] is None


def test_missing_or_unknown_sources_fall_back_to_original_response():
    answer = report({"text":"Done", "sources":["E99"], "confirmation_quote":"approved"})
    assert validate_decision(answer, [{"text":"user: approved"}])[0] is None
    assert validate_decision("Not structured", [])[0] is None


def test_multisession_recall_and_abstention_metrics():
    retrieval = {"trace":{"candidates":[{"session_id":"a"},{"session_id":"a"}]}, "evidence":[{"id":"a"}]}
    metrics = evidence_metrics(retrieval, {"evidence":["a","b"]})
    assert metrics["recall_at_20"] == .5 and not metrics["packed_all_required"]
    assert evidence_metrics(retrieval, {"evidence":[]})["recall_at_20"] is None
