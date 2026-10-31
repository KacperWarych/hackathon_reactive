import json

import pytest

from conftest import FakeModels, archive, put_question, put_session
from decision_memory.config import Config
from decision_memory.entries import add_entry, export_entries, parse_transcript
from decision_memory.index import Index
from decision_memory.retrieval import Retriever
from decision_memory.store import Store


def test_parse_and_validate():
    turns = parse_transcript('Seller: Hello\nCustomer: Cena za wysoka.\nProszę zadzwonić jutro.')
    assert [t['role'] for t in turns] == ['assistant', 'user']
    assert 'jutro' in turns[1]['content']
    for value in ('', 'unlabelled text', 'Customer:'):
        with pytest.raises(ValueError):
            parse_transcript(value)


def test_entry_persists_reimport_is_idempotent_and_searchable(store, env):
    put_session(store, 'h1', 's1', 'Original camera')
    put_session(store, 'h2', 's2', 'Other person')
    sid = add_entry(store, 'dev', 'h1', '2023-05-25 10:00', 'Customer: The camera budget is approved.')
    assert add_entry(store, 'dev', 'h1', '2023-05-25 10:00', 'Customer: The camera budget is approved.') == sid
    assert len(store.sessions('dev', 'h1')) == 2
    other = Store(store.path)
    assert sid in other.valid_sessions('dev', 'h1')
    other.close()
    exported = json.loads(export_entries(store, 'dev', 'h1'))
    assert [s['session_id'] for s in exported['sessions']] == [sid]
    source = env / 'source.tar.gz'
    archive(source, {'histories.jsonl': [{'history_id': 'h1', 'sessions': [{'session_id': 's1', 'date': '2023-05-20', 'turns': [{'turn_id': 't1', 'role': 'user', 'content': 'Original camera'}]}]}]})
    store.ingest(source, 'dev')
    assert sid in store.valid_sessions('dev', 'h1')
    assert sid not in store.valid_sessions('dev', 'h2')
    models = FakeModels()
    Index(store, models, Config()).build('dev')
    question = put_question(store)
    evidence = Retriever(store, models).retrieve(question, 'hybrid')['evidence']
    assert sid in {e['id'] for e in evidence}
    earlier = put_question(store, qid='earlier', date='2023-05-21')
    assert sid not in {e['id'] for e in Retriever(store, models).retrieve(earlier, 'bm25')['evidence']}


def test_invalid_entry_does_not_write(store):
    put_session(store, 'h1', 's1', 'Original')
    for date, text in [('invalid', 'Customer: Hello'), ('2023-05-20', '')]:
        with pytest.raises(ValueError):
            add_entry(store, 'dev', 'h1', date, text)
    assert len(store.sessions('dev', 'h1')) == 1
