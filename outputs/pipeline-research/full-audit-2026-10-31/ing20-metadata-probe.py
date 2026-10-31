"""Verify public salesgen identity metadata survives (or is lost) at ingestion."""
import json
import os
import tempfile
from collections import Counter
from pathlib import Path

from decision_memory.store import Store

SOURCE = Path("/Users/kacperwarych/Desktop/hackathon reactive ai/salesgen_dataset_fail")


def run():
    # Deliberately read only public source plus README; never calls_gold/gold files.
    histories = [json.loads(line) for line in (SOURCE / "public/histories.jsonl").read_text().splitlines()]
    sessions = [session for history in histories for session in history["sessions"]]
    fields = ("call_id", "customer_id", "customer_name", "product_id")
    counts = Counter(session["meta"]["customer_id"] for session in sessions)
    readme = (SOURCE / "README.md").read_text()
    contract = [{"line": n, "text": line} for n, line in enumerate(readme.splitlines(), 1)
                if n in (23, 24, 68, 69, 70)]
    with tempfile.TemporaryDirectory(prefix="ing20-metadata-") as work:
        os.environ["MEMORY_DATA_DIR"] = work
        store = Store(Path(work) / "memory.sqlite")
        report = store.ingest(SOURCE / "public", "salesgen")
        schema = [dict(row) for row in store.db.execute("PRAGMA table_info(sessions)")]
        returned = store.sessions("salesgen", histories[0]["history_id"])
        output = {
            "source": str(SOURCE / "public"), "contract": contract,
            "sessions": len(sessions), "distinct_customer_ids": len(counts),
            "customers_with_multiple_calls": sum(n > 1 for n in counts.values()),
            "metadata_coverage": {field: sum(field in session.get("meta", {}) for session in sessions) for field in fields},
            "ingested": report, "stored_session_columns": [row["name"] for row in schema],
            "returned_session_count": len(returned),
            "returned_sessions_with_meta": sum("meta" in row for row in returned),
            "stored_content_payload_is_turns_only": set(store.db.execute("SELECT * FROM contents LIMIT 1").description[n][0]
                                                          for n in range(2)) == {"hash", "turns"},
            "evaluation_files_read": False,
        }
        store.close()
    return output


if __name__ == "__main__":
    result = run()
    Path(__file__).with_name("ing20-metadata-results.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
