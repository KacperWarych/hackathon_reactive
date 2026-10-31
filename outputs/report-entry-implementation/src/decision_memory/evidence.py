"""Choose short original exchanges under independent token, excerpt, and message budgets."""
from __future__ import annotations

import re
from collections import defaultdict

from .memory import cues

STOP = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being", "i", "me", "my", "we", "our",
    "you", "your", "it", "its", "this", "that", "these", "those", "what", "which", "who", "how", "when",
    "where", "why", "do", "does", "did", "can", "could", "would", "should", "have", "has", "had", "of",
    "for", "to", "in", "on", "at", "and", "or", "with", "from", "as", "by", "about", "still", "current",
    "currently", "latest", "now", "changed", "change", "changes", "history", "decision", "recorded",
    "relevant", "reconstruct", "purchase", "deal", "blocks", "blocking",
    "co", "czy", "jak", "jaki", "jaka", "jakie", "który", "która", "które", "którego", "dla", "dlaczego",
    "jest", "są", "był", "była", "było", "były", "się", "nie", "na", "od", "w", "z", "ze", "o", "za", "przez", "oraz", "lub", "ale", "ten", "ta", "te", "oferty", "oferta", "zakupu",
    "kupił", "kupiła", "nadal", "wciąż", "aktualny", "aktualna", "aktualne", "najbardziej", "powód",
}
TEMPORAL = re.compile(
    r"\b(still|current\w*|latest|most recent|now|chang\w*|updat\w*|history|resolved|remaining|"
    r"aktualn\w*|ostatni\w*|nadal|wciąż|zmian\w*|histori\w*|pozosta\w*|rozwiąz\w*)\b", re.IGNORECASE)
AGGREGATION = re.compile(r"\b(how many|count|total|percentage|proportion|ilu|ile|liczb\w*|odset\w*|procent\w*)\b",
                         re.IGNORECASE)


def keywords(text):
    return set(re.findall(r"\w+(?:[-.:/]\w+)*", text.casefold())) - STOP


def extract_options(question, ranked, chunks, originals, tokenizer, config, memory):
    query = keywords(question["question"])
    sources, options = {}, []
    for idx in ranked:
        row = chunks[idx]
        sid = row["session_id"]
        if sid not in sources:
            full, spans, units = "", [], []
            for turn in originals[sid]:
                start = len(full)
                prefix = f"{turn['role']}: "
                full += prefix + turn["content"] + "\n"
                spans.append((start, len(full), turn))
                for unit in memory.records(turn):
                    lo = start + len(prefix) + unit["start"]
                    hi = start + len(prefix) + unit["end"]
                    units.append({"start": start if unit["start"] == 0 else lo, "end": hi,
                                  "cues": unit["cues"], "role": turn["role"], "turn_id": turn["turn_id"]})
            sources[sid] = full, spans, units
        full, spans, units = sources[sid]
        eligible = [u for u in units if u["end"] > row["start"] and u["start"] < row["end"]]
        # A chunk can discuss multiple topics. Retain up to two distinct local options.
        eligible.sort(key=lambda u: (-len(query & keywords(full[u["start"]:u["end"]])), u["start"]))
        for unit in eligible[:2]:
            lo, hi = unit["start"], unit["end"]
            current = next(i for i, (a, b, _) in enumerate(spans) if a <= lo < b)
            # A short answer needs its initiating exchange; keep role labels in both directions.
            if current and config.context_tokens and len(tokenizer.encode(full[lo:hi], add_special_tokens=False)) <= config.context_tokens:
                a, b, _ = spans[current - 1]
                prev = tokenizer(full[a:b], add_special_tokens=False, return_offsets_mapping=True)["offset_mapping"]
                lo = a if len(prev) <= config.context_tokens else a + prev[-config.context_tokens][0]
            if current + 1 < len(spans):
                a, b, _ = spans[current + 1]
                if len(tokenizer.encode(full[a:b], add_special_tokens=False)) <= config.context_tokens:
                    hi = b
            a, b, turn = next(x for x in spans if x[0] <= lo < x[1])
            prefix = "" if lo == a else f"{turn['role']} (continued): "
            text = prefix + full[lo:hi]
            # Units are bounded, but surrounding context and subword tokenization can exceed the cap.
            offsets = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)["offset_mapping"]
            if len(offsets) > config.excerpt_tokens:
                hi = lo + offsets[config.excerpt_tokens - 1][1] - len(prefix)
                text = prefix + full[lo:hi]
            covered = query & keywords(text)
            options.append({"id": sid, "date": row["date"], "iso": row.get("iso", row["date"]),
                            "text": text, "start": lo, "end": hi, "covered": covered,
                            "cues": cues(text), "user_update": unit["role"] == "user" and
                            bool(set(unit["cues"]) & {"update", "confirmation", "concern"}),
                            "turn_ids": [t["turn_id"] for a, b, t in spans if a < hi and b > lo],
                            "candidate": idx, "rank": len(options)})
    return options


def select_options(question, options, config, tokenizer, size):
    selected, covered, seen = [], set(), set()
    temporal = bool(TEMPORAL.search(question["question"]))

    def redundant(option):
        normalized = re.sub(r"\s+", " ", option["text"]).strip().casefold()
        # Identical wording can describe separate events; retain separate sources for count questions.
        if normalized in seen and not AGGREGATION.search(question["question"]):
            return True
        return any(option["id"] == old["id"] and
                   max(0, min(option["end"], old["end"]) - max(option["start"], old["start"])) /
                   max(1, min(option["end"]-option["start"], old["end"]-old["start"])) > .5 for old in selected)

    def render(items):
        grouped = defaultdict(list)
        for item in items:
            grouped[item["id"]].append(item)
        return [{"id": sid, "date": group[0]["date"],
                 "text": "\n[... excerpt gap ...]\n".join(x["text"] for x in sorted(group, key=lambda x: x["start"])),
                 "turn_ids": list(dict.fromkeys(t for x in group for t in x["turn_ids"]))}
                for sid, group in grouped.items()]

    remaining = list(options)
    while remaining and len(selected) < config.max_excerpts:
        latest = max((o["iso"] for o in remaining if o["user_update"] and o["covered"]), default="")
        # Reward missing question facets and reserve room for a later buyer update.
        def utility(o, latest=latest):
            return (1 / (1 + o["rank"] * .12) + .3 * len(o["covered"] - covered) +
                    (1.1 if temporal and selected and o["user_update"] and o["covered"] and o["iso"] == latest and
                     not any(s["user_update"] and s["iso"] >= latest for s in selected) else 0))
        option = max(remaining, key=utility)
        remaining.remove(option)
        if redundant(option):
            continue
        trial = render(selected + [option])
        text = "\n".join(e["text"] for e in trial)
        if (sum(len(e["text"]) for e in trial) > config.evidence_chars or
                len(tokenizer.encode(text, add_special_tokens=False)) > config.evidence_tokens or
                size(question, trial) > config.max_message_chars):
            continue
        selected.append(option)
        covered.update(option["covered"])
        seen.add(re.sub(r"\s+", " ", option["text"]).strip().casefold())
    return render(selected), selected


def expansion_reason(question, top_chunks):
    """Conservative search planning hints; these are not calibrated answerability checks."""
    if not top_chunks:
        return "no_candidates"
    query = keywords(question)
    covered = set().union(*(keywords(c["text"]) for c in top_chunks))
    if query - covered:
        return "missing_question_terms"
    if TEMPORAL.search(question):
        relevant = [c for c in top_chunks if query & keywords(c["text"])]
        dated = {c.get("iso", c["date"]) for c in relevant}
        user_updates = []
        for chunk in relevant:
            blocks = re.findall(r"(?:^|\n)user(?: \(continued\))?:\s*(.*?)(?=\n(?:assistant|user)(?: \(continued\))?:|\Z)",
                                chunk["text"], re.DOTALL)
            user_updates.extend(b for b in blocks if set(cues(b)) & {"update", "confirmation"}
                                and "hypothetical" not in cues(b))
        if len(dated) < 2 or not user_updates:
            return "missing_update_evidence"
    return None
