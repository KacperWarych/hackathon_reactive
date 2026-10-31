from __future__ import annotations

import json
import sys
import time

import numpy as np

from .chunks import chunk_scheme, chunk_turns
from .config import Config, digest
from .memory import Memory
from .operations import serialized_operation


class Index:
    def __init__(self, store, models, config: Config):
        self.store, self.models, self.config = store, models, config
        self.scheme = chunk_scheme(config, models.revisions[config.embedding])

    @serialized_operation
    def build(self, split, histories=None, dense=True):
        start = time.monotonic()
        memory = Memory(self.store, self.models.tokenizer, self.models.key)
        self.store.db.execute("CREATE TABLE IF NOT EXISTS embedding_texts "
                              "(model_key TEXT, text_hash TEXT, chunk_id TEXT, PRIMARY KEY(model_key,text_hash))")
        # Backfill existing vectors once; future append-only updates use indexed hash lookups.
        marker = "embedding-text-cache:" + self.models.key
        if dense and not self.store.db.execute("SELECT 1 FROM metadata WHERE key=?", (marker,)).fetchone():
            with self.store.db:
                old = self.store.db.execute("SELECT c.text,e.chunk_id FROM embeddings e "
                                            "JOIN chunks c ON c.chunk_id=e.chunk_id WHERE e.model_key=?",
                                            (self.models.key,)).fetchall()
                self.store.db.executemany("INSERT OR IGNORE INTO embedding_texts VALUES(?,?,?)",
                                         ((self.models.key, digest(r["text"]), r["chunk_id"]) for r in old))
                self.store.db.execute("INSERT OR REPLACE INTO metadata VALUES(?,?)", (marker, "1"))
        rows = self.store.db.execute("SELECT DISTINCT history_id FROM sessions WHERE split=? ORDER BY history_id", (split,))
        wanted = set(histories) if histories is not None else None
        hids = [r[0] for r in rows if wanted is None or r[0] in wanted]
        total = embedded = 0
        for hid in hids:
            for session in self.store.sessions(split, hid):
                key = session["content_hash"]
                indexed = self.store.db.execute("SELECT 1 FROM indexed WHERE content_hash=? AND scheme=?",
                                                (key, self.scheme)).fetchone()
                turns = json.loads(session["turns"])
                memory.prepare(turns)
                if not indexed:
                    chunks = chunk_turns(turns, self.models.tokenizer, self.config)
                    with self.store.db:
                        for chunk in chunks:
                            cid = digest([key, self.scheme, chunk["start"], chunk["end"]])
                            self.store.db.execute("INSERT OR IGNORE INTO chunks VALUES(?,?,?,?,?,?,?,?)", (
                                cid, key, self.scheme, chunk["text"], chunk["start"], chunk["end"],
                                json.dumps(chunk["turn_ids"]), chunk["tokens"]))
                        self.store.db.execute("INSERT INTO indexed VALUES(?,?)", (key, self.scheme))
                if dense:
                    missing = self.store.db.execute(
                        "SELECT c.* FROM chunks c LEFT JOIN embeddings e ON c.chunk_id=e.chunk_id AND e.model_key=? "
                        "WHERE c.content_hash=? AND c.scheme=? AND e.chunk_id IS NULL ORDER BY c.start",
                        (self.models.key, key, self.scheme)).fetchall()
                    for i in range(0, len(missing), self.config.batch_size):
                        batch = missing[i:i+self.config.batch_size]
                        # Appending turns changes the session hash, but stable excerpts can reuse vectors.
                        reused, fresh = {}, []
                        for row in batch:
                            old = self.store.db.execute(
                                "SELECT e.vector FROM embedding_texts t JOIN embeddings e "
                                "ON e.chunk_id=t.chunk_id AND e.model_key=t.model_key "
                                "WHERE t.model_key=? AND t.text_hash=?", (self.models.key, digest(row["text"]))).fetchone()
                            if old:
                                reused[row["chunk_id"]] = np.frombuffer(old[0], dtype=np.float32)
                            else:
                                fresh.append(row)
                        fresh_vecs = self.models.embed([r["text"] for r in fresh]) if fresh else []
                        reused.update({r["chunk_id"]: v for r, v in zip(fresh, fresh_vecs)})
                        with self.store.db:
                            for row in batch:
                                vec = reused[row["chunk_id"]]
                                self.store.db.execute("INSERT OR REPLACE INTO embeddings VALUES(?,?,?,?)", (
                                    row["chunk_id"], self.models.key, len(vec), vec.astype(np.float32).tobytes()))
                                self.store.db.execute("INSERT OR IGNORE INTO embedding_texts VALUES(?,?,?)", (
                                    self.models.key, digest(row["text"]), row["chunk_id"]))
                        embedded += len(fresh)
                total += 1
                if total % 100 == 0:
                    print(f"index {split}: {total} sessions, {embedded} new vectors, {time.monotonic()-start:.1f}s", file=sys.stderr, flush=True)
            print(f"indexed history {hid}", file=sys.stderr, flush=True)
        return {"histories": len(hids), "sessions": total, "new_vectors": embedded,
                "new_memory_turns": memory.misses, "cached_memory_turns": memory.hits,
                "seconds": round(time.monotonic()-start, 2), "scheme": self.scheme}

    def candidates(self, question, dense):
        sessions = self.store.db.execute(
            "SELECT s.*, i.content_hash ready FROM sessions s LEFT JOIN indexed i ON s.content_hash=i.content_hash "
            "AND i.scheme=? WHERE s.split=? AND s.history_id=? AND s.iso<=?",
            (self.scheme, question["split"], question["history_id"], question["iso"])).fetchall()
        if any(s["ready"] is None for s in sessions):
            raise RuntimeError("History has unindexed sessions. Run memory index for this split/manifest first.")
        rows = self.store.db.execute(
            "SELECT c.*,s.session_id,s.date,s.iso,s.history_id,e.vector FROM sessions s "
            "JOIN chunks c ON s.content_hash=c.content_hash AND c.scheme=? "
            "LEFT JOIN embeddings e ON c.chunk_id=e.chunk_id AND e.model_key=? "
            "WHERE s.split=? AND s.history_id=? AND s.iso<=? ORDER BY s.iso,s.position,c.start",
            (self.scheme, self.models.key, question["split"], question["history_id"], question["iso"])).fetchall()
        result, vecs = [], []
        for row in rows:
            item = dict(row)
            vector = item.pop("vector")
            if dense and vector is None:
                raise RuntimeError("Dense vectors are missing. Run memory index without --lexical-only.")
            if dense:
                vecs.append(np.frombuffer(vector, dtype=np.float32))
            item["turn_ids"] = json.loads(item["turn_ids"])
            item["key"] = item["session_id"] + ":" + item["chunk_id"]
            result.append(item)
        return result, np.array(vecs) if dense else None
