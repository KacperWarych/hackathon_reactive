"""Validate and persist manually entered conversations independently of the UI."""
import json
import re

from .config import digest
from .operations import serialized_operation
from .store import iso_date

ROLES = {"user": "user", "customer": "user", "client": "user", "klient": "user",
         "assistant": "assistant", "seller": "assistant", "agent": "assistant", "sprzedawca": "assistant"}


def parse_transcript(text):
    if not text.strip():
        raise ValueError("Enter a conversation before saving.")
    if len(text) > 100000:
        raise ValueError("Keep each conversation under 100,000 characters.")
    turns = []
    for line in text.splitlines():
        if not line.strip():
            continue
        match = re.match(r"^\s*([\w]+)\s*:\s*(.*)$", line)
        if match and match[1].lower() in ROLES:
            turns.append({"role": ROLES[match[1].lower()], "content": match[2].strip()})
        elif not turns:
            raise ValueError("Start with a speaker label, for example Customer: or Seller:.")
        else:
            turns[-1]["content"] += "\n" + line.strip()
    if any(not t["content"].strip() for t in turns):
        raise ValueError("Each speaker turn must contain text.")
    return [{"turn_id": f"t_{i+1}", **turn} for i, turn in enumerate(turns)]


@serialized_operation
def add_entry(store, split, history_id, date, transcript):
    turns = parse_transcript(transcript)
    iso = iso_date(date)
    if not store.valid_sessions(split, history_id):
        raise ValueError("Choose an existing dataset and history.")
    sid = "manual_" + digest([split, history_id, iso, turns])[:24]
    key = digest(turns)
    with store.db:
        store.db.execute("INSERT OR IGNORE INTO contents VALUES(?,?)", (key, json.dumps(turns, ensure_ascii=False)))
        store.db.execute("INSERT OR IGNORE INTO sessions VALUES(?,?,?,?,?,?,?)", (
            split, history_id, sid, date, iso, 1000000, key))
        store.db.execute("INSERT OR IGNORE INTO manual_entries VALUES(?,?,?)", (split, history_id, sid))
    return sid


def export_entries(store, split, history_id):
    ids = {r[0] for r in store.db.execute(
        "SELECT session_id FROM manual_entries WHERE split=? AND history_id=?", (split, history_id))}
    sessions = [{"session_id": s["session_id"], "date": s["date"], "turns": json.loads(s["turns"])}
                for s in store.sessions(split, history_id) if s["session_id"] in ids]
    return json.dumps({"history_id": history_id, "sessions": sessions}, ensure_ascii=False) + "\n"
