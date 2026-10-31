"""Strict display validation, not a claim of automatic semantic verification."""
import json
import re

SECTIONS = ("goals", "concerns", "changes", "resolutions", "missing_information", "interpretations", "next_questions")


DECISION_REPAIR = ("\nThe previous decision output was invalid. Return a corrected complete JSON object. "
                   "Use double quotes for all JSON keys and strings and escape embedded double quotes. "
                   "Keep all seven required arrays, valid evidence labels, and only traceable confirmations.")


def decision_prompt(topic):
    return (
        f"Reconstruct the recorded decision history relevant to: {topic}\n"
        "Return valid JSON, using double-quoted keys and strings (escape embedded double quotes). "
        "Respond directly with the final-answer marker and JSON, without a preliminary explanation. "
        "Keep entries concise, at most three per section. Include only people and decisions relevant to the topic; "
        "do not fill sections with unrelated people from retrieved excerpts. "
        "Return one JSON object with arrays goals, concerns, changes, resolutions, missing_information, "
        "interpretations, next_questions. Every entry must have text and sources (an array of evidence labels "
        "such as E1). Cite supporting evidence for every entry. Missing information describes what sources "
        "leave unknown, not a factual claim that an event never happened. Only buyer/user confirmation can "
        "establish acceptance or resolution; assistant suggestions and silence cannot. Keep hypothetical "
        "options separate from commitments and completed actions. Use empty arrays when unsupported. "
        "A changed fact or routine belongs in changes; it is not a resolution. Resolutions require an earlier "
        "concern and an explicit statement that it was solved or a proposal accepted. If that is absent, "
        "return an empty resolutions array. "
        "For resolutions include a confirmation_quote copied exactly from a user statement in a cited excerpt. "
        "That quote must include an explicit word such as resolved, cleared, approved, accepted, confirmed, "
        "completed, works, fixed, signed, paid, or Polish potwierdzam, akceptuję, rozwiązany, "
        "and must not be hypothetical or negated. "
        "Add the cited labels in brackets after the JSON so citation mapping can verify them."
    )


def validate_decision(answer, evidence):
    start = answer.find("{")
    if start < 0:
        return None, "Reactor did not return a structured decision view."
    try:
        obj, _ = json.JSONDecoder().raw_decode(answer[start:])
    except ValueError:
        return None, "The structured response could not be parsed."
    if not isinstance(obj, dict) or set(obj) != set(SECTIONS):
        return None, "The response is missing expected decision sections."
    sources = {f"E{i}": e for i, e in enumerate(evidence, 1)}
    for section in SECTIONS:
        if not isinstance(obj[section], list):
            return None, "A decision section is not a list."
        for entry in obj[section]:
            if not isinstance(entry, dict) or not isinstance(entry.get("text"), str) or not entry["text"].strip():
                return None, "A decision entry has no text."
            labels = entry.get("sources")
            if not isinstance(labels, list) or not labels or any(not isinstance(s, str) or s not in sources for s in labels):
                return None, "A decision entry has missing or unknown sources."
            if section == "resolutions":
                quote = entry.get("confirmation_quote")
                user_blocks = []
                for label in labels:
                    source = sources[label]
                    for span in source.get("source_spans", []):
                        # Only trusted structured spans produced from original turns qualify.
                        # Legacy evidence without provenance is intentionally unresolved.
                        if (span.get("role") == "user" and span.get("turn_id")
                                and source.get("source_hash")
                                and span.get("source_hash") == source["source_hash"]
                                and isinstance(span.get("excerpt_start"), int)
                                and isinstance(span.get("excerpt_end"), int)
                                and 0 <= span["excerpt_start"] < span["excerpt_end"] <= len(source["text"])
                                and source["text"][span["excerpt_start"]:span["excerpt_end"]] == span.get("text")):
                            user_blocks.append(span["text"])
                matches = [block for block in user_blocks if isinstance(quote, str) and quote in block]
                if not isinstance(quote, str) or len(quote) < 8 or not matches:
                    return None, "A proposed resolution lacks a matching user confirmation quote."
                speculative = (r"\b(if|might|could|would|should|maybe|hopefully|once|unresolved|"
                               r"not|never|haven't|hasn't|isn't|wasn't|don't|didn't|"
                               r"nie|nigdy|gdyby|jeśli|jezeli|jeżeli|może|moze|być może|"
                               r"chyba|prawdopodobnie|ewentualnie)\b")
                # Check the selected turn context as well as the quote: a shortened
                # quote must not hide a nearby negation or conditional premise.
                if all(re.search(speculative, block, re.IGNORECASE) for block in matches):
                    return None, "A proposed resolution uses speculative or negated language."
                positive = (r"\b(resolved|cleared|approved|accepted|confirmed|completed|works|working|fixed|signed|paid|"
                            r"potwierdzam|akceptuję|akceptuje|zatwierdzam|zaakceptowane|zaakceptowana|"
                            r"zatwierdzone|zatwierdzona|rozwiązany|rozwiązana|rozwiązane|rozwiązaliśmy|"
                            r"naprawione|naprawiona|podpisane|podpisana|zapłacone)\b")
                if not re.search(positive, quote, re.IGNORECASE):
                    return None, "A proposed resolution lacks an explicit confirmation statement."
    return obj, None
