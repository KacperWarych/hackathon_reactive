from __future__ import annotations

import json
import sqlite3
import tarfile
from datetime import datetime
from pathlib import Path

from .config import data_root, digest


def iso_date(raw: str) -> str:
    for fmt in ("%Y/%m/%d (%a) %H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).isoformat(timespec="minutes")
        except ValueError:
            pass
    raise ValueError(f"Unsupported date: {raw!r}")


def dataset_files(source: Path):
    """Read public inputs and optional evaluation gold without extracting archives."""
    if source.is_dir():
        public = source / "public" if (source / "public").is_dir() else source
        inputs = [public / "histories.jsonl", public / "questions.jsonl"]
        for path in inputs:
            if not path.is_file():
                raise FileNotFoundError(f"Missing dataset input: {path}")
        gold = source / "gold" / "gold.jsonl"
        if gold.is_file():
            inputs.append(gold)
        for path in inputs:
            with path.open("rb") as stream:
                yield path.name, stream
    else:
        with tarfile.open(source, "r|gz") as tar:
            for member in tar:
                name = Path(member.name).name
                if member.isfile() and name in {"histories.jsonl", "questions.jsonl", "gold.jsonl"}:
                    with tar.extractfile(member) as stream:
                        yield name, stream


class Store:
    def __init__(self, path: Path | None = None):
        self.path = path or data_root() / "memory.sqlite"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=60)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS contents (hash TEXT PRIMARY KEY, turns TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions (
          split TEXT, history_id TEXT, session_id TEXT, date TEXT, iso TEXT, position INT, content_hash TEXT,
          PRIMARY KEY(split, history_id, session_id));
        CREATE TABLE IF NOT EXISTS questions (
          split TEXT, question_id TEXT, history_id TEXT, question TEXT, question_date TEXT, iso TEXT,
          PRIMARY KEY(split, question_id));
        CREATE TABLE IF NOT EXISTS chunks (
          chunk_id TEXT PRIMARY KEY, content_hash TEXT, scheme TEXT, text TEXT,
          start INT, end INT, turn_ids TEXT, tokens INT);
        CREATE INDEX IF NOT EXISTS chunk_content ON chunks(content_hash, scheme);
        CREATE TABLE IF NOT EXISTS indexed (content_hash TEXT, scheme TEXT, PRIMARY KEY(content_hash, scheme));
        CREATE TABLE IF NOT EXISTS embeddings (
          chunk_id TEXT, model_key TEXT, dimensions INT, vector BLOB,
          PRIMARY KEY(chunk_id, model_key));
        CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS manual_entries (
          split TEXT, history_id TEXT, session_id TEXT,
          PRIMARY KEY(split, history_id, session_id));
        """)

    def close(self):
        self.db.close()

    def questions(self, split: str, ids: list[str] | None = None):
        rows = [dict(x) for x in self.db.execute(
            "SELECT * FROM questions WHERE split=? ORDER BY history_id,iso,question_id", (split,))]
        if ids is not None:
            wanted = set(ids)
            rows = [r for r in rows if r["question_id"] in wanted]
            if {r["question_id"] for r in rows} != wanted:
                raise ValueError("Manifest contains questions not ingested in this split.")
        return rows

    def sessions(self, split, history_id):
        return [dict(x) for x in self.db.execute(
            "SELECT s.*,c.turns FROM sessions s JOIN contents c ON s.content_hash=c.hash "
            "WHERE split=? AND history_id=? ORDER BY iso,position", (split, history_id))]

    def stats(self):
        return [dict(x) for x in self.db.execute(
            "SELECT split,count(DISTINCT history_id) histories,count(*) sessions FROM sessions GROUP BY split")]

    def valid_sessions(self, split, history_id):
        return {r[0] for r in self.db.execute(
            "SELECT session_id FROM sessions WHERE split=? AND history_id=?", (split, history_id))}

    def ingest(self, archive: Path, split: str, history_ids: set[str] | None = None):
        """Stream an archive or dataset directory; keep gold evaluation-only."""
        if not split or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in split):
            raise ValueError("Split names may contain only letters, digits, underscores and hyphens.")
        count = {"histories": 0, "sessions": 0, "questions": 0}
        gold_path = data_root() / "evaluation" / f"gold-{split}.jsonl"
        gold_path.parent.mkdir(parents=True, exist_ok=True)
        for name, stream in dataset_files(archive):
            if name == "gold.jsonl":
                temp = gold_path.with_suffix(".tmp")
                with temp.open("wb") as out:
                    for line in stream:
                        json.loads(line)  # fail on malformed source
                        out.write(line)
                temp.replace(gold_path)
                continue
            seen = set()
            for line in stream:
                if not line.strip():
                    continue
                row = json.loads(line)
                hid = row["history_id"]
                if history_ids is not None and hid not in history_ids:
                    continue
                identity = row.get("question_id", hid)
                if identity in seen:
                    raise ValueError(f"Duplicate {identity} in {name}")
                seen.add(identity)
                if name == "questions.jsonl":
                    self.db.execute("INSERT OR REPLACE INTO questions VALUES(?,?,?,?,?,?)", (
                        split, row["question_id"], hid, row["question"], row["question_date"],
                        iso_date(row["question_date"])))
                    count["questions"] += 1
                else:
                    with self.db:
                        self.db.execute("DELETE FROM sessions WHERE split=? AND history_id=? AND session_id NOT IN "
                                        "(SELECT session_id FROM manual_entries WHERE split=? AND history_id=?)", (split, hid, split, hid))
                        session_ids = set()
                        for pos, session in enumerate(row["sessions"]):
                            sid = session["session_id"]
                            if sid in session_ids:
                                raise ValueError(f"Duplicate session {sid} in {hid}")
                            session_ids.add(sid)
                            turns = session["turns"]
                            for turn in turns:
                                if turn["role"] not in ("user", "assistant") or not isinstance(turn["content"], str):
                                    raise ValueError(f"Invalid turn in {sid}")
                            key = digest(turns)
                            self.db.execute("INSERT OR IGNORE INTO contents VALUES(?,?)", (
                                key, json.dumps(turns, ensure_ascii=False)))
                            self.db.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?,?)", (
                                split, hid, sid, session["date"], iso_date(session["date"]), pos, key))
                            count["sessions"] += 1
                    count["histories"] += 1
            self.db.commit()
        self.db.execute("INSERT OR REPLACE INTO metadata VALUES(?,?)", (
            f"archive:{split}", json.dumps({"path": str(archive), "bytes": archive.stat().st_size, **count})))
        self.db.commit()
        return count
