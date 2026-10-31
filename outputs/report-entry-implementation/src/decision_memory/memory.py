"""Cached extractive memory. Cue labels are search hints, never verified deal states."""
from __future__ import annotations

import json
import re
from collections import OrderedDict

from .config import digest

SCHEME = "extractive-turn-v2"
CUES = {
    "concern": r"\b(block\w*|concern\w*|cannot|can't|unable|waiting|pending|unresolved|problem\w*|issue\w*|blok\w*|obaw\w*|czek\w*|oczek\w*|nierozw\w*|wątpliw\w*)\b",
    "requirement": r"\b(require\w*|need\w*|must|budget|contract|integration|security|procurement|wymag\w*|potrzeb\w*|budżet\w*|umow\w*|integrac\w*|bezpieczeń\w*)\b",
    "update": r"\b(chang\w*|updat\w*|replac\w*|cancel\w*|instead|no longer|now|zmian\w*|zmieni\w*|aktualiz\w*|zamiast|teraz|już nie)\b",
    "confirmation": r"\b(resolv\w*|clear\w*|approv\w*|accept\w*|confirm\w*|complet\w*|works|fixed|signed|paid|purchased|rozwiąza\w*|zatwierdz\w*|zaakcept\w*|potwierdz\w*|zakończ\w*|działa|napraw\w*|podpis\w*|opłac\w*|zapłac\w*)\b",
    "hypothetical": r"\b(if|might|could|would|should|maybe|hopefully|once|propos\w*|offer\w*|jeśli|gdyby|mógł\w*|mogł\w*|może|propon\w*|oferuj\w*)\b",
}


def cues(text):
    return [name for name, pattern in CUES.items() if re.search(pattern, text, re.IGNORECASE)]


class Memory:
    def __init__(self, store, tokenizer, tokenizer_key=None):
        self.store, self.tokenizer = store, tokenizer
        self.scheme = digest([SCHEME, tokenizer_key or getattr(tokenizer, "name_or_path", type(tokenizer).__name__)])
        self.local = OrderedDict()
        self.hits = self.misses = self.inference_hits = self.inference_misses = 0
        store.db.executescript("""
        CREATE TABLE IF NOT EXISTS memory_turns (
          content_key TEXT, scheme TEXT, records TEXT NOT NULL,
          PRIMARY KEY(content_key, scheme));
        CREATE TABLE IF NOT EXISTS retrieval_inference (
          kind TEXT, cache_key TEXT, value TEXT NOT NULL,
          PRIMARY KEY(kind, cache_key));
        """)

    def records(self, turn):
        # Exclude session/date/turn IDs: bind those from the current source, never the cache.
        key = digest([turn["role"], turn["content"]])
        if key in self.local:
            self.hits += 1
            self.local.move_to_end(key)
            return self.local[key]
        cached = self.store.db.execute(
            "SELECT records FROM memory_turns WHERE content_key=? AND scheme=?", (key, self.scheme)).fetchone()
        if cached:
            self.hits += 1
            result = json.loads(cached[0])
        else:
            self.misses += 1
            text = turn["content"]
            offsets = self.tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)["offset_mapping"]
            # Keep short turns whole; use bounded, sentence-aware units for long monologues.
            boundaries = {m.end() for m in re.finditer(r"[.!?](?:\s+|$)|\n+", text)}
            result, at = [], 0
            while at < len(offsets):
                cap = min(at + 200, len(offsets))
                choices = [i for i in range(at + 60, cap + 1) if offsets[i - 1][1] in boundaries]
                end = cap if cap == len(offsets) else choices[-1] if choices else cap
                lo, hi = offsets[at][0], offsets[end - 1][1]
                result.append({"start": lo, "end": hi, "cues": cues(text[lo:hi])})
                at = end
            with self.store.db:
                self.store.db.execute("INSERT OR IGNORE INTO memory_turns VALUES(?,?,?)",
                                      (key, self.scheme, json.dumps(result)))
        self.local[key] = result
        if len(self.local) > 512:
            self.local.popitem(last=False)
        return result

    def prepare(self, turns):
        for turn in turns:
            self.records(turn)

    def inference_get(self, kind, key):
        row = self.store.db.execute(
            "SELECT value FROM retrieval_inference WHERE kind=? AND cache_key=?", (kind, key)).fetchone()
        if row is None:
            self.inference_misses += 1
            return None
        self.inference_hits += 1
        return json.loads(row[0])

    def inference_put(self, kind, key, value):
        with self.store.db:
            self.store.db.execute("INSERT OR REPLACE INTO retrieval_inference VALUES(?,?,?)",
                                  (kind, key, json.dumps(value)))
            self.store.db.execute("DELETE FROM retrieval_inference WHERE rowid IN "
                                  "(SELECT rowid FROM retrieval_inference ORDER BY rowid DESC LIMIT -1 OFFSET 8192)")
