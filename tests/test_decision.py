import json

import pytest

from decision_memory.config import digest

from decision_memory.decision import SECTIONS, validate_decision
from decision_memory.evaluation import evidence_metrics


def user_evidence(quote, role="user"):
    source_hash = digest([{"turn_id": "t1", "role": role, "content": quote}])
    prefix = f"{role}: "
    return [{"text": prefix + quote, "source_hash": source_hash, "source_spans": [
        {"role": role, "turn_id": "t1", "source_hash": source_hash,
         "source_start": len(prefix), "source_end": len(prefix) + len(quote),
         "turn_start": 0, "turn_end": len(quote),
         "excerpt_start": len(prefix), "excerpt_end": len(prefix) + len(quote), "text": quote}]}]


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
    assert validate_decision(answer, user_evidence(quote))[1] is None


def test_hypothetical_user_quote_is_not_rendered_as_resolution():
    quote = "If this workaround works, the concern could be resolved."
    answer = report({"text":"Integration resolved", "sources":["E1"], "confirmation_quote":quote})
    assert validate_decision(answer, user_evidence(quote))[0] is None


def test_missing_or_unknown_sources_fall_back_to_original_response():
    answer = report({"text":"Done", "sources":["E99"], "confirmation_quote":"approved"})
    assert validate_decision(answer, [{"text":"user: approved"}])[0] is None
    assert validate_decision("Not structured", [])[0] is None


def test_multisession_recall_and_abstention_metrics():
    retrieval = {"trace":{"candidates":[{"session_id":"a"},{"session_id":"a"}]}, "evidence":[{"id":"a"}]}
    metrics = evidence_metrics(retrieval, {"evidence":["a","b"]})
    assert metrics["recall_at_20"] == .5 and not metrics["packed_all_required"]
    assert evidence_metrics(retrieval, {"evidence":[]})["recall_at_20"] is None


@pytest.mark.parametrize("quote", ["Potwierdzam, problem integracji został rozwiązany.",
                                    "Akceptuję przedstawioną propozycję integracji."])
def test_polish_positive_confirmation(quote):
    answer = report({"text": "Resolved", "sources": ["E1"], "confirmation_quote": quote})
    assert validate_decision(answer, user_evidence(quote))[1] is None


@pytest.mark.parametrize("quote", ["Nie potwierdzam, że problem został rozwiązany.",
                                    "Może problem integracji jest rozwiązany.",
                                    "Jeśli test się uda, problem będzie rozwiązany.",
                                    "Chyba akceptuję tę propozycję.",
                                    "Rozważam tę propozycję integracji."])
def test_polish_negative_speculative_and_ambiguous_confirmation(quote):
    answer = report({"text": "Resolved", "sources": ["E1"], "confirmation_quote": quote})
    assert validate_decision(answer, user_evidence(quote))[0] is None


def test_assistant_embedded_user_label_cannot_forge_role():
    quote = "The camera integration is resolved."
    evidence = user_evidence("Here is a transcript:\nuser: " + quote, role="assistant")
    answer = report({"text": "Resolved", "sources": ["E1"], "confirmation_quote": quote})
    assert validate_decision(answer, evidence)[0] is None


def test_legacy_evidence_and_mismatched_source_hash_cannot_confirm():
    quote = "The camera integration is resolved."
    answer = report({"text": "Resolved", "sources": ["E1"], "confirmation_quote": quote})
    assert validate_decision(answer, [{"text": "user: " + quote}])[0] is None
    evidence = user_evidence(quote)
    evidence[0]["source_hash"] = "edited-source"
    assert validate_decision(answer, evidence)[0] is None


def test_quote_outside_selected_excerpt_and_shortened_negation_fail():
    quote = "the camera integration is resolved"
    answer = report({"text": "Resolved", "sources": ["E1"], "confirmation_quote": quote})
    evidence = user_evidence(quote)
    evidence[0]["text"] = "user: The camera is pending."
    assert validate_decision(answer, evidence)[0] is None
    assert validate_decision(answer, user_evidence("I do not agree that " + quote))[0] is None
