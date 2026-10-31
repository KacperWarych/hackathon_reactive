"""Demonstrate missing durable entry-refresh state using only temporary data."""
import json
import sys
from pathlib import Path

PROJECT = Path('/Users/kacperwarych/Desktop/hackathon reactive ai')
sys.path.insert(0, str(PROJECT / 'tests'))
from conftest import env, indexed, store  # noqa: F401 - pytest fixtures
from test_investigation_ui import button, prepared_app
from streamlit.testing.v1 import AppTest


def test_pending_report_entry_index_retry_lost_after_new_session(indexed, store, env, monkeypatch):
    import decision_memory.report_entry_ui as entry_ui
    app, _ = prepared_app(monkeypatch)

    def fail(*args, **kwargs):
        raise RuntimeError('Audit: simulated indexing failure')

    monkeypatch.setattr(entry_ui.Index, 'build', fail)
    next(t for t in app.text_area if t.label == 'New entry').input('The new budget is approved.')
    button(app, 'Save entry and refresh report').click().run()
    assert not app.exception
    assert any(b.label == 'Retry entry refresh' for b in app.button)
    assert store.db.execute('SELECT count(*) FROM manual_entries').fetchone()[0] == 1

    fresh = AppTest.from_file(str(PROJECT / 'app.py')).run()
    button(fresh, 'Previous reports').click().run()
    button(fresh, 'Open report').click().run()
    assert not fresh.exception
    assert not any(b.label == 'Retry entry refresh' for b in fresh.button)
    assert store.db.execute('SELECT count(*) FROM manual_entries').fetchone()[0] == 1
    result = {'pending_entry_survives_in_db': True,
              'retry_visible_in_original_session': True,
              'retry_visible_in_fresh_session': False}
    (Path(__file__).parent / 'ui-recovery-results.json').write_text(json.dumps(result, indent=2)+'\n')
