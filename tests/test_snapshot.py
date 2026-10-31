from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from conftest import put_session

from decision_memory.operations import serialized_operation
from decision_memory.snapshot import eligible_fingerprint, is_current


@pytest.mark.parametrize('change', ['add', 'delete', 'date', 'content'])
def test_snapshot_tracks_complete_eligible_population(indexed, store, change):
    q, _ = indexed
    retrieval = {'question': {**q, 'history_revision': eligible_fingerprint(store, q)}}
    assert is_current(store, retrieval)
    if change == 'add':
        put_session(store, 'h1', 'new', 'Previously unretrieved unrelated fact.')
    elif change == 'delete':
        store.db.execute("DELETE FROM sessions WHERE session_id='s1'")
    elif change == 'date':
        store.db.execute("UPDATE sessions SET iso='2023-05-21T10:00' WHERE session_id='s1'")
    else:
        put_session(store, 'h1', 's1', 'Corrected original content.')
    assert not is_current(store, retrieval)


def test_future_and_other_history_changes_do_not_stale_snapshot(indexed, store):
    q, _ = indexed
    before = eligible_fingerprint(store, q)
    put_session(store, 'h1', 'future-new', 'Future fact.', date='2024-01-01 12:00')
    put_session(store, 'other', 'other-new', 'Other customer fact.')
    assert eligible_fingerprint(store, q) == before
    assert not is_current(store, {'question': q})


def test_operations_serialize_threads_and_allow_nested_services():
    entered, release, second_entered = Event(), Event(), Event()

    @serialized_operation
    def inner():
        return True

    @serialized_operation
    def first():
        assert inner()
        entered.set()
        assert release.wait(5)

    @serialized_operation
    def second():
        second_entered.set()

    with ThreadPoolExecutor(2) as pool:
        one = pool.submit(first)
        assert entered.wait(5)
        two = pool.submit(second)
        try:
            assert not second_entered.wait(.1)
        finally:
            release.set()
        one.result()
        two.result()
    assert second_entered.is_set()
