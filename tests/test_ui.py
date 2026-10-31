import json
from pathlib import Path
from streamlit.testing.v1 import AppTest
APP = Path(__file__).resolve().parents[1]/"app.py"

def button(app, label):
    return next(b for b in app.button if b.label == label)

def test_empty_library_has_setup_instructions(env):
    app = AppTest.from_file(str(APP)).run()
    assert not app.exception
    assert any("Import the supplied" in i.value for i in app.info)

def test_minimal_home_and_navigation(indexed, env):
    app = AppTest.from_file(str(APP)).run()
    assert not app.exception
    assert not app.tabs
    assert [t.label for t in app.text_area] == ["Your question"]
    button(app, "Create report").click().run()
    assert any("Write a question" in w.value for w in app.warning)
    button(app, "Previous reports").click().run()
    assert any("No matching reports" in i.value for i in app.info)
    button(app, "Add entry").click().run()
    assert any(t.label == "Conversation transcript" for t in app.text_area)

def test_report_persists_and_reopens(indexed, env, monkeypatch):
    import decision_memory.retrieval as retrieval
    for name in ("REACTOR_BASE_URL", "REACTOR_AGENT_ID", "REACTOR_ACCESS_KEY"):
        monkeypatch.setenv(name, "")
    captured=[]
    class FakeRetriever:
        def __init__(self,*args): pass
        def retrieve(self,q,mode):
            captured.append(q)
            return {"question":q,"evidence":[],"trace":{"message_chars":0,"mode":mode}}
    monkeypatch.setattr(retrieval,"Retriever",FakeRetriever)
    app = AppTest.from_file(str(APP)).run()
    app.text_area[0].input("What changed in the budget?")
    button(app,"Create report").click().run()
    assert not app.exception
    assert [t.label for t in app.tabs] == ["Answer and evidence","Decision history","Evaluation"]
    saved=list((env/'ui_reports').glob('*.json'))
    assert len(saved)==1
    assert json.loads(saved[0].read_text())["retrieval"]["question"]["question"] == captured[0]["question"]
    fresh=AppTest.from_file(str(APP)).run()
    button(fresh,"Previous reports").click().run()
    button(fresh,"Open report").click().run()
    assert not fresh.exception
    assert fresh.title[0].value == captured[0]["question"]
    assert len(captured)==1

def test_add_conversation_form(indexed, env, monkeypatch, store):
    import decision_memory.entry_ui as entry_ui
    from conftest import FakeModels
    from decision_memory.index import Index
    monkeypatch.setattr(entry_ui,"Index",lambda store,models,config:Index(store,FakeModels(),config))
    app=AppTest.from_file(str(APP)).run()
    button(app,"Add entry").click().run()
    next(t for t in app.text_area if t.label=="Conversation transcript").input("Customer: The camera budget was approved today.")
    button(app,"Save conversation").click().run()
    assert not app.exception
    assert any("saved and searchable" in s.value for s in app.success)
    assert store.db.execute("SELECT count(*) FROM manual_entries").fetchone()[0]==1


def test_entry_index_failure_can_retry(indexed, env, monkeypatch, store):
    import decision_memory.entry_ui as entry_ui
    class BrokenIndex:
        def __init__(self, *args): pass
        def build(self, *args): raise RuntimeError("model unavailable")
    monkeypatch.setattr(entry_ui, "Index", BrokenIndex)
    app = AppTest.from_file(str(APP)).run(timeout=30)
    button(app, "Add entry").click().run()
    next(t for t in app.text_area if t.label == "Conversation transcript").input("Customer: Camera budget approved.")
    next(b for b in app.button if b.label == "Save conversation").click().run(timeout=30)
    assert any("saved, but indexing" in w.value for w in app.warning)
    assert store.db.execute("SELECT count(*) FROM manual_entries").fetchone()[0] == 1
    from conftest import FakeModels
    from decision_memory.index import Index
    monkeypatch.setattr(entry_ui, "Index", lambda store, models, config: Index(store, FakeModels(), config))
    app.run()
    next(b for b in app.button if b.label == "Retry indexing").click().run(timeout=30)
    assert not app.exception
    assert any("saved and searchable" in s.value for s in app.success)
    assert store.db.execute("SELECT count(*) FROM manual_entries").fetchone()[0] == 1

