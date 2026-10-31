"""Report entry capture uses real persistence, indexing, and versioned regeneration."""

import json

from test_investigation_ui import button, prepared_app


def journal(env):
    return json.loads(next((env / "investigations").glob("*/journal.json")).read_text())


def enter(app, text="The camera lens budget is approved after a new customer call."):
    next(t for t in app.text_area if t.label == "New entry").input(text)
    button(app, "Save entry and refresh report").click().run()
    assert not app.exception


def test_note_refreshes_same_report_and_includes_new_evidence(indexed, store, env, monkeypatch):
    app, _ = prepared_app(monkeypatch)
    path = next((env / "ui_reports").glob("*.json"))
    before = json.loads(path.read_text())
    enter(app)
    after = json.loads(path.read_text())
    assert after["id"] == before["id"]
    assert after["investigation_id"] == before["investigation_id"]
    assert after["revision_number"] == before["revision_number"] + 1
    sid = store.db.execute("SELECT session_id FROM manual_entries WHERE history_id='h1'").fetchone()[0]
    assert store.db.execute("SELECT COUNT(*) FROM manual_entries").fetchone()[0] == 1
    latest = journal(env)["revisions"][-1]
    assert sid in {e["id"] for e in latest["retrieval"]["evidence"]}
    assert latest["answer_record"] and latest["decision_record"]
    assert latest["retrieval"]["question"]["iso"] >= before["retrieval"]["question"]["iso"]
    assert any("have been refreshed" in s.value for s in app.success)
    assert next(t for t in app.text_area if t.label == "New entry").value == ""


def test_invalid_transcript_is_not_saved(indexed, store, env, monkeypatch):
    app, _ = prepared_app(monkeypatch)
    next(r for r in app.radio if r.label == "Entry type").set_value("Conversation transcript")
    enter(app, "No speaker labels")
    assert any("speaker label" in e.value for e in app.error)
    assert store.db.execute("SELECT COUNT(*) FROM manual_entries").fetchone()[0] == 0
    assert journal(env)["revisions"][-1]["number"] == 1


def test_transcript_keeps_speakers_and_backdated_entry_keeps_report_date(indexed, store, env, monkeypatch):
    from datetime import date

    app, _ = prepared_app(monkeypatch)
    before = journal(env)["revisions"][-1]
    next(r for r in app.radio if r.label == "Entry type").set_value("Conversation transcript")
    next(d for d in app.date_input if d.label == "Entry date").set_value(date(2023, 5, 24))
    enter(app, "Seller: Is the camera lens budget approved?\nCustomer: Yes, it is approved.")
    after = journal(env)["revisions"][-1]
    assert after["retrieval"]["question"]["iso"] == before["retrieval"]["question"]["iso"]
    session = next(s for s in store.sessions("dev", "h1") if s["session_id"].startswith("manual_"))
    assert [t["role"] for t in json.loads(session["turns"])] == ["assistant", "user"]
    assert session["session_id"] in {e["id"] for e in after["retrieval"]["evidence"]}
    from decision_memory.store import iso_date

    assert all(iso_date(e["date"]) <= before["retrieval"]["question"]["iso"]
               for e in after["retrieval"]["evidence"])


def test_generation_failure_retries_without_resaving_entry(indexed, store, env, monkeypatch):
    app, adapter = prepared_app(monkeypatch)
    path = next((env / "ui_reports").glob("*.json"))
    before = json.loads(path.read_text())
    adapter.fail = "decision"
    enter(app)
    assert json.loads(path.read_text())["revision_id"] == before["revision_id"]
    assert journal(env)["revisions"][-1]["status"] == "failed"
    adapter.fail = None
    button(app, "Restart memory and refresh entry").click().run()
    assert not app.exception
    assert store.db.execute("SELECT COUNT(*) FROM manual_entries").fetchone()[0] == 1
    assert journal(env)["revisions"][-1]["status"] == "complete"
    assert json.loads(path.read_text())["revision_number"] == 3


def test_index_failure_retries_and_earlier_versions_are_read_only(indexed, store, env, monkeypatch):
    import decision_memory.report_entry_ui as entry_ui

    app, _ = prepared_app(monkeypatch)
    build = entry_ui.Index.build

    def fail(*args, **kwargs):
        raise RuntimeError("Index unavailable")

    monkeypatch.setattr(entry_ui.Index, "build", fail)
    enter(app)
    assert journal(env)["revisions"][-1]["number"] == 1
    assert any("Index unavailable" in w.value for w in app.warning)
    monkeypatch.setattr(entry_ui.Index, "build", build)
    button(app, "Retry entry refresh").click().run()
    assert not app.exception
    assert store.db.execute("SELECT COUNT(*) FROM manual_entries").fetchone()[0] == 1
    assert journal(env)["revisions"][-1]["number"] == 2
    earlier = journal(env)["revisions"][1]["id"]
    next(s for s in app.selectbox if s.label == "Saved version").select(earlier).run()
    assert not app.exception
    assert not any(b.label == "Save entry and refresh report" for b in app.button)
