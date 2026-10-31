from __future__ import annotations

from .config import Config, digest


def chunk_turns(turns, tokenizer, config: Config):
    """Character offsets refer to an immutable role-labeled session rendering."""
    rendered, spans = "", []
    for t in turns:
        start = len(rendered)
        rendered += f"{t['role']}: {t['content']}\n"
        spans.append((start, len(rendered), t["turn_id"], t["role"]))
    if not rendered.strip():
        return []
    enc = tokenizer(rendered, add_special_tokens=False, return_offsets_mapping=True)
    offsets = enc["offset_mapping"]
    boundaries = {end for _, end, _, _ in spans}
    rows, start = [], 0
    while start < len(offsets):
        ideal = min(start + config.target_tokens, len(offsets))
        cap = min(start + config.max_tokens - 16, len(offsets))  # room for a continuation speaker label
        choices = [i for i in range(start + 1, cap + 1)
                   if offsets[i - 1][1] in boundaries and i - start >= config.target_tokens // 2]
        end = min(choices, key=lambda i: abs(i - ideal)) if choices else ideal
        lo, hi = offsets[start][0], offsets[end - 1][1]
        matching = [(a, b, tid, role) for a, b, tid, role in spans if b > lo and a < hi]
        text = rendered[lo:hi]
        if matching and lo > matching[0][0]:
            text = f"{matching[0][3]} (continued): " + text
        rows.append({"text": text, "start": lo, "end": hi,
                     "turn_ids": [x[2] for x in matching],
                     "tokens": len(tokenizer.encode(text, add_special_tokens=False))})
        if end == len(offsets):
            break
        start = max(start + 1, end - config.overlap_tokens)
    return rows


def chunk_scheme(config, revision):
    return digest({"version": 1, "tokenizer": revision, "target": config.target_tokens,
                   "maximum": config.max_tokens, "overlap": config.overlap_tokens})
