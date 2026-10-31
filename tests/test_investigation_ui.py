"""Exercise the real report screen and revision service with a transport double."""

import json
from pathlib import Path

from conftest import FakeModels
from streamlit.testing.v1 import AppTest
from test_investigations import Adapter

APP = Path(__file__).resolve().parents[1] / "app.py"


def button(app, label):
    return next(b for b in app.button if b.label == label)


def prepared_app(monkeypatch):
    import decision_memory.investigations as investigations
    import decision_memory.models as models

    adapter = Adapter()
    monkeypatch.setattr(investigations, "Reactor", lambda: adapter)
    monkeypatch.setattr(models, "Models", lambda *args: FakeModels())
    for name in ("REACTOR_BASE_URL", "REACTOR_AGENT_ID", "REACTOR_ACCESS_KEY"):
        monkeypatch.setenv(name, "test-value")
    app = AppTest.from_file(str(APP)).run()
    app.text_area[0].input("Which camera lens is approved?")
    button(app, "Create report").click().run()
    assert not app.exception
    return app, adapter


def test_followup_updates_both_sections_and_versions_survive_reopening(
    indexed, env, monkeypatch
):
    app, adapter = prepared_app(monkeypatch)
    next(t for t in app.text_area if t.label == "Follow-up prompt").input(
        "Focus on the remaining budget concern."
    )
    button(app, "Revise report").click().run()
    assert not app.exception
    assert sum(c[0] == "--new-history" for c in adapter.calls) == 1
    journal = json.loads(
        next((env / "investigations").glob("*/journal.json")).read_text()
    )
    assert [r["status"] for r in journal["revisions"]] == [
        "saved",
        "complete",
        "complete",
    ]
    latest = journal["current_revision"]
    report_path = next((env / "ui_reports").glob("*.json"))
    assert json.loads(report_path.read_text())["revision_id"] == latest
    earlier = journal["revisions"][1]["id"]
    next(s for s in app.selectbox if s.label == "Saved version").select(earlier).run()
    assert not app.exception
    assert any("latest saved version" in i.value for i in app.info)
    assert json.loads(report_path.read_text())["revision_id"] == earlier
    next(s for s in app.selectbox if s.label == "Saved version").select(latest).run()
    calls = len(adapter.calls)
    fresh = AppTest.from_file(str(APP)).run()
    button(fresh, "Previous reports").click().run()
    button(fresh, "Open report").click().run()
    assert not fresh.exception
    assert any("Version 2" in c.value for c in fresh.caption)
    assert len(adapter.calls) == calls


def test_failed_followup_shows_recovery_and_preserves_previous_report(
    indexed, env, monkeypatch
):
    app, adapter = prepared_app(monkeypatch)
    report_path = next((env / "ui_reports").glob("*.json"))
    before = json.loads(report_path.read_text())
    adapter.fail = "decision"
    next(t for t in app.text_area if t.label == "Follow-up prompt").input(
        "Explain the concern."
    )
    button(app, "Revise report").click().run()
    assert not app.exception
    assert json.loads(report_path.read_text())["revision_id"] == before["revision_id"]
    assert button(app, "Restart memory and retry")
    adapter.fail = None
    button(app, "Restart memory and retry").click().run()
    assert not app.exception
    assert json.loads(report_path.read_text())["revision_number"] == 3
    assert sum(c[0] == "--new-history" for c in adapter.calls) == 2


def test_build_decision_view_uses_one_request_and_can_recover(indexed, env, monkeypatch):
    app, adapter = prepared_app(monkeypatch)
    calls = len(adapter.calls)
    button(app, "Build decision view").click().run()
    assert not app.exception
    assert len(adapter.calls) == calls + 1
    adapter.fail = "decision"
    button(app, "Build decision view").click().run()
    assert not app.exception
    # Rerender exposes the saved failed attempt's recovery controls.
    app.run()
    adapter.fail = None
    calls = len(adapter.calls)
    button(app, "Restart memory and retry").click().run()
    assert not app.exception
    assert not app.error
    assert len(adapter.calls) == calls + 2  # reset plus decision, no answer generation
