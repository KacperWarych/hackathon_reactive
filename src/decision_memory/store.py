from __future__ import annotations

import json
import sqlite3
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

from .config import data_root, digest
from .operations import serialized_operation


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

    @serialized_operation
    def ingest(self, archive: Path, split: str, history_ids: set[str] | None = None):
        """Validate the complete input, then publish it under one SQL rollback boundary.

        Gold is immutable for an existing split. Use a fresh split to change gold;
        its file is published before the transaction makes the split selectable.
        """
        if not split or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in split):
            raise ValueError("Split names may contain only letters, digits, underscores and hyphens.")
        if self.db.in_transaction:
            raise ValueError("Finish the pending database transaction before importing a dataset.")
        staged = {}
        for name, stream in dataset_files(archive):
            if name in staged:
                raise ValueError(f"Duplicate dataset file: {name}")
            rows = []
            for number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except (ValueError, UnicodeDecodeError) as exc:
                    raise ValueError(f"Invalid JSON in {name} line {number}: {exc}") from exc
                if not isinstance(row, dict):
                    raise ValueError(f"Expected an object in {name} line {number}")  # noqa: TRY004 — malformed imported data
                rows.append(row)
            staged[name] = rows
        if not staged or not ({"histories.jsonl", "questions.jsonl"} & staged.keys()):
            raise ValueError("Dataset contains no histories.jsonl or questions.jsonl input.")

        def required(row, field, context):
            value = row.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Missing or invalid {field} in {context}: expected a nonempty string")
            return value

        def unique(value, seen, context):
            if value in seen:
                raise ValueError(f"Duplicate {value} in {context}")
            seen.add(value)

        histories = staged.get("histories.jsonl", [])
        questions = staged.get("questions.jsonl", [])
        hids, qids = set(), set()
        for row in histories:
            hid = required(row, "history_id", "histories.jsonl")
            unique(hid, hids, "histories.jsonl")
            if not isinstance(row.get("sessions"), list):
                raise ValueError(f"Missing or invalid sessions in history {hid}")  # noqa: TRY004 — malformed imported data
            sids = set()
            for session in row["sessions"]:
                if not isinstance(session, dict):
                    raise ValueError(f"Invalid session in history {hid}")  # noqa: TRY004 — malformed imported data
                sid = required(session, "session_id", f"history {hid}")
                unique(sid, sids, f"history {hid}")
                iso_date(required(session, "date", f"session {sid}"))
                if not isinstance(session.get("turns"), list):
                    raise ValueError(f"Missing or invalid turns in session {sid}")  # noqa: TRY004 — malformed imported data
                tids = set()
                for turn in session["turns"]:
                    if not isinstance(turn, dict):
                        raise ValueError(f"Invalid turn in session {sid}")  # noqa: TRY004 — malformed imported data
                    tid = required(turn, "turn_id", f"session {sid}")
                    unique(tid, tids, f"session {sid}")
                    if turn.get("role") not in ("user", "assistant") or not isinstance(turn.get("content"), str):
                        raise ValueError(f"Invalid role or content for turn {tid} in session {sid}")
        existing_hids = {r[0] for r in self.db.execute("SELECT DISTINCT history_id FROM sessions WHERE split=?", (split,))}
        for row in questions:
            qid = required(row, "question_id", "questions.jsonl")
            unique(qid, qids, "questions.jsonl")
            hid = required(row, "history_id", f"question {qid}")
            required(row, "question", f"question {qid}")
            iso_date(required(row, "question_date", f"question {qid}"))
            if hid not in hids | existing_hids:
                raise ValueError(f"Question {qid} references unknown history_id {hid}")
        gold_ids = set()
        for row in staged.get("gold.jsonl", []):
            qid = required(row, "question_id", "gold.jsonl")
            unique(qid, gold_ids, "gold.jsonl")
            if qid not in qids:
                raise ValueError(f"Gold references unknown question_id {qid}")
        histories = [r for r in histories if history_ids is None or r["history_id"] in history_ids]
        questions = [r for r in questions if history_ids is None or r["history_id"] in history_ids]
        selected_qids = {r["question_id"] for r in questions}
        count = {"histories": len(histories), "sessions": sum(len(r["sessions"]) for r in histories), "questions": len(questions)}
        gold_path = data_root() / "evaluation" / f"gold-{split}.jsonl"
        gold_bytes = None
        if "gold.jsonl" in staged:
            gold_bytes = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in staged["gold.jsonl"]
                                 if r["question_id"] in selected_qids).encode()
            if gold_path.exists():
                existing_gold = [json.loads(line) for line in gold_path.read_bytes().splitlines() if line.strip()]
                if existing_gold != [json.loads(line) for line in gold_bytes.splitlines()]:
                    raise ValueError("Changing existing gold requires a fresh split; existing gold was preserved.")
                gold_bytes = None
            elif self.db.execute("SELECT 1 FROM sessions WHERE split=? UNION ALL SELECT 1 FROM questions WHERE split=? LIMIT 1", (split, split)).fetchone():
                raise ValueError("Publishing gold requires a fresh split; existing data was preserved.")
        temp = None
        published = False
        try:
            if gold_bytes is not None:
                gold_path.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(dir=gold_path.parent, prefix=f".gold-{split}-", delete=False) as out:
                    temp = Path(out.name)
                    out.write(gold_bytes)
            with self.db:
                for row in histories:
                    hid = row["history_id"]
                    self.db.execute("DELETE FROM sessions WHERE split=? AND history_id=? AND session_id NOT IN "
                                    "(SELECT session_id FROM manual_entries WHERE split=? AND history_id=?)", (split, hid, split, hid))
                    for pos, session in enumerate(row["sessions"]):
                        turns = session["turns"]
                        key = digest(turns)
                        self.db.execute("INSERT OR IGNORE INTO contents VALUES(?,?)", (key, json.dumps(turns, ensure_ascii=False)))
                        self.db.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?,?)", (
                            split, hid, session["session_id"], session["date"], iso_date(session["date"]), pos, key))
                for row in questions:
                    self.db.execute("INSERT OR REPLACE INTO questions VALUES(?,?,?,?,?,?)", (
                        split, row["question_id"], row["history_id"], row["question"], row["question_date"], iso_date(row["question_date"])))
                self.db.execute("INSERT OR REPLACE INTO metadata VALUES(?,?)", (
                    f"archive:{split}", json.dumps({"path": str(archive), "bytes": archive.stat().st_size, **count})))
                if temp is not None:
                    temp.replace(gold_path)
                    published = True
            return count
        except BaseException:
            if published:
                gold_path.unlink(missing_ok=True)
            raise
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)
