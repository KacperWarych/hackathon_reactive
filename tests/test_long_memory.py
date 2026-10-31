import json
from dataclasses import replace

from conftest import FakeModels, put_question, put_session
from decision_memory.config import Config, digest
from decision_memory.evidence import expansion_reason
from decision_memory.index import Index
from decision_memory.memory import Memory
from decision_memory.retrieval import Retriever, message_size
from decision_memory.store import iso_date


def save_turns(store, turns, sid='long', date='2023/05/20 (Sat) 10:00'):
    key = digest(turns)
    with store.db:
        store.db.execute('INSERT OR IGNORE INTO contents VALUES(?,?)', (key, json.dumps(turns)))
        store.db.execute('INSERT OR REPLACE INTO sessions VALUES(?,?,?,?,?,?,?)',
                         ('dev', 'h1', sid, date, iso_date(date), 0, key))


class CountingModels(FakeModels):
    def __init__(self):
        self.query_calls = 0
        self.reranked = 0

    def embed(self, texts, query=False):
        if query:
            self.query_calls += len(texts)
        return super().embed(texts, query)

    def rerank(self, question, docs):
        self.reranked += len(docs)
        return super().rerank(question, docs)



def test_long_conversation_retains_short_confirmation_and_original_roles(store):
    turns = [{'turn_id': f'n{i}', 'role': 'user', 'content': 'Unrelated chatter about weather. ' * 60}
             for i in range(30)]
    turns += [{'turn_id': 'offer', 'role': 'assistant', 'content': 'Would the camera integration workaround solve the blocker?'},
              {'turn_id': 'accept', 'role': 'user', 'content': 'That works. I accept it.'}]
    save_turns(store, turns)
    q = put_question(store, text='Is the camera integration blocker resolved?')
    model = FakeModels()
    Index(store, model, Config()).build('dev')
    result = Retriever(store, model).retrieve(q, 'hybrid')
    text = '\n'.join(e['text'] for e in result['evidence'])
    assert 'assistant: Would the camera integration workaround solve the blocker?' in text
    assert 'user: That works. I accept it.' in text
    assert result['trace']['evidence_tokens'] <= 2000
    assert len(text) < 8000 < sum(len(t['content']) for t in turns)
    assert {'offer', 'accept'} <= set(result['evidence'][0]['turn_ids'])



def test_budget_is_enforced_across_many_topics_and_sources(store):
    for i in range(35):
        put_session(store, 'h1', f's{i}', f'Camera lens model {i} budget waiting. ' * 80)
    q = put_question(store)
    model = FakeModels()
    config = replace(Config(), evidence_tokens=450, max_excerpts=3)
    Index(store, model, config).build('dev')
    result = Retriever(store, model, config).retrieve(q, 'bm25')
    assert result['evidence']
    assert result['trace']['excerpt_count'] <= 3
    assert result['trace']['evidence_tokens'] <= 450
    assert result['trace']['evidence_chars'] <= config.evidence_chars
    assert message_size(q, result['evidence']) <= config.max_message_chars
    assert all('user' in e['text'] for e in result['evidence'])



def test_missing_update_triggers_one_bounded_search_without_rescoring_initial_candidates(store):
    for i in range(65):
        put_session(store, 'h1', f's{i}', f'Camera lens budget pending for model RF-{i}.')
    q = put_question(store, text='What still blocks the camera lens purchase?')
    model = CountingModels()
    config = Config()
    Index(store, model, config).build('dev')
    result = Retriever(store, model, config).retrieve(q, 'full')
    assert result['trace']['expansion_reason'] == 'missing_update_evidence'
    assert len(result['trace']['expansion_queries']) == 1
    assert len(result['trace']['searches']) == 2
    assert model.reranked <= config.rerank_k + config.expansion_k
    assert result['trace']['reranked_documents'] == model.reranked



def test_complete_first_pass_skips_extra_search(indexed, store):
    q, model = indexed
    result = Retriever(store, model).retrieve(q, 'full')
    assert result['trace']['expansion_queries'] == []
    assert len(result['trace']['searches']) == 1



def test_neural_cache_survives_new_retriever_instances_and_is_question_specific(indexed, store):
    q, _ = indexed
    model = CountingModels()
    first = Retriever(store, model).retrieve(q, 'rerank')
    counts = model.query_calls, model.reranked
    second = Retriever(store, model).retrieve(q, 'rerank')
    assert (model.query_calls, model.reranked) == counts
    assert second['evidence'] == first['evidence']
    assert second['trace']['cache']['inference_hits'] > 0
    assert second['trace']['reranked_documents'] == 0
    Retriever(store, model).retrieve({**q, 'question': 'What camera lens budget was resolved?'}, 'rerank')
    assert model.query_calls > counts[0] and model.reranked > counts[1]



def test_source_changes_invalidate_reused_retriever_and_keep_future_out(indexed, store):
    q, model = indexed
    retriever = Retriever(store, model)
    first = retriever.retrieve(q, 'bm25')
    put_session(store, 'h1', 'new', 'The camera lens budget now has a new pending security concern.', '2023/05/30 (Tue) 10:00')
    Index(store, model, Config()).build('dev')
    result = retriever.retrieve(q, 'bm25')
    assert result['trace']['history_revision'] != first['trace']['history_revision']
    assert 'new' in {e['id'] for e in result['evidence']}
    assert 'future' not in {e['id'] for e in result['evidence']}



def test_incremental_memory_extracts_only_new_or_edited_turns(store):
    model = FakeModels()
    memory = Memory(store, model.tokenizer)
    initial = [{'turn_id': 'a', 'role': 'user', 'content': 'The camera lens budget is pending.'}]
    memory.prepare(initial)
    assert memory.misses == 1
    memory.prepare(initial + [{'turn_id': 'b', 'role': 'assistant', 'content': 'I could offer a pilot.'}])
    assert memory.misses == 2 and memory.hits == 1
    # Metadata and source IDs must be rebound, not inherited from another history.
    memory.prepare([{**initial[0], 'turn_id': 'different-history-turn'}])
    assert memory.misses == 2
    memory.prepare([{**initial[0], 'content': 'The camera lens budget is approved.'}])
    assert memory.misses == 3



def test_incremental_index_reuses_stable_prefix_vectors(store):
    turns = [{'turn_id': f't{i}', 'role': 'user', 'content': f'Camera lens RF-{i} budget pending. ' * 180}
             for i in range(4)]
    save_turns(store, turns)
    model = FakeModels()
    index = Index(store, model, Config())
    first = index.build('dev')
    save_turns(store, turns + [{'turn_id': 'new', 'role': 'user', 'content': 'Camera lens budget approved.'}])
    second = index.build('dev')
    assert second['new_memory_turns'] == 1
    assert second['cached_memory_turns'] == 4
    assert 0 < second['new_vectors'] < first['new_vectors']



def test_later_resolution_and_original_concern_both_survive_packing(store):
    put_session(store, 'h1', 'raised', 'The camera integration is blocked and procurement approval is pending.', '2023/05/01 (Mon) 10:00')
    put_session(store, 'h1', 'proposal', 'We could fix the camera integration with a pilot if you accept it.', '2023/05/20 (Sat) 10:00', role='assistant')
    put_session(store, 'h1', 'confirmed', 'The camera integration is resolved. Procurement approval is still pending.', '2023/05/29 (Mon) 10:00')
    q = put_question(store, text='What still blocks the camera integration purchase?')
    model = FakeModels()
    Index(store, model, Config()).build('dev')
    result = Retriever(store, model).retrieve(q, 'full')
    assert {'raised', 'confirmed'} <= {e['id'] for e in result['evidence']}
    assert any('still pending' in e['text'] for e in result['evidence'])
    assert all(e['id'] != 'proposal' or e['text'].startswith('assistant:') for e in result['evidence'])
    assert not result['trace']['expansion_queries']



def test_expansion_checks_missing_facets_without_claiming_answerability():
    rows = [{'text': 'Camera lens budget approved.', 'date': '2023-05-20'}]
    assert expansion_reason('Which camera lens is approved?', rows) is None
    assert expansion_reason('Is camera lens procurement approved?', rows) == 'missing_question_terms'
    assert expansion_reason('What is the latest camera lens budget?', rows) == 'missing_update_evidence'



def test_empty_history_returns_empty_bounded_bundle(store):
    q = put_question(store)
    result = Retriever(store, FakeModels()).retrieve(q, 'full')
    assert result['evidence'] == []
    assert result['trace']['evidence_tokens'] == 0
    assert result['trace']['excerpt_count'] == 0
    assert result['trace']['reranked_documents'] == 0


def test_seller_proposal_does_not_satisfy_buyer_update_search():
    rows = [{'text': 'user: The camera integration is blocked.', 'date': '2023-05-01'},
            {'text': 'assistant: I could offer an approved camera integration pilot.', 'date': '2023-05-20'}]
    assert expansion_reason('What still blocks the camera integration?', rows) == 'missing_update_evidence'


def test_polish_temporal_questions_retain_buyer_updates():
    rows = [{'text': 'user: Integracja czeka na zatwierdzenie.', 'date': '2023-05-01'},
            {'text': 'user: Potwierdzam, integracja została zatwierdzona.', 'date': '2023-05-20'}]
    assert expansion_reason('Jaka jest aktualna integracja?', rows) is None


def test_campaign_count_prompt_requires_complete_coverage(indexed, store):
    from decision_memory.retrieval import reactor_question
    q, model = indexed
    q = {**q, 'question': 'Ilu klientów odmówiło zakupu?'}
    result = Retriever(store, model).retrieve(q, 'bm25')
    assert result['trace']['coverage_warning']
    assert 'complete population coverage' in reactor_question(q['question'])


def test_latency_percentiles_cover_small_samples():
    from decision_memory.evaluation import latency_summary
    assert latency_summary([]) == {'p50_seconds': None, 'p95_seconds': None}
    assert latency_summary([None, 2.]) == {'p50_seconds': 2., 'p95_seconds': 2.}
    assert latency_summary([1., 3.])['p50_seconds'] == 2.


def test_identical_wording_on_distinct_dates_retains_latest_provenance(store):
    text = "The camera integration concern is resolved."
    put_session(store, 'h1', 'older', text, '2023/05/01 (Mon) 10:00')
    put_session(store, 'h1', 'newer', text, '2023/05/29 (Mon) 10:00')
    q = put_question(store, text='What is the latest camera integration state?')
    model = FakeModels()
    Index(store, model, Config()).build('dev')
    result = Retriever(store, model).retrieve(q, 'bm25')
    assert {'older', 'newer'} == {e['id'] for e in result['evidence']}
    for evidence in result['evidence']:
        assert evidence['source_hash']
        for span in evidence['source_spans']:
            assert span['source_hash'] == evidence['source_hash']
            assert evidence['text'][span['excerpt_start']:span['excerpt_end']] == span['text']
            assert span['role'] == 'user'


def test_packed_source_roles_ignore_embedded_user_labels(store):
    from decision_memory.decision import SECTIONS, validate_decision
    quote = 'The camera integration concern is resolved.'
    save_turns(store, [{'turn_id': 'seller', 'role': 'assistant',
                        'content': 'Transcript example:\nuser: ' + quote}])
    q = put_question(store, text='Is the camera integration resolved?')
    model = FakeModels()
    Index(store, model, Config()).build('dev')
    evidence = Retriever(store, model).retrieve(q, 'bm25')['evidence']
    assert evidence and all(s['role'] == 'assistant' for e in evidence for s in e['source_spans'])
    obj = {key: [] for key in SECTIONS}
    obj['resolutions'] = [{'text': 'Resolved', 'sources': ['E1'], 'confirmation_quote': quote}]
    assert validate_decision(json.dumps(obj), evidence)[0] is None


def test_packed_genuine_user_confirmation_is_valid(store):
    from decision_memory.decision import SECTIONS, validate_decision
    quote = 'Potwierdzam, problem integracji został rozwiązany.'
    put_session(store, 'h1', 'confirmed', quote)
    q = put_question(store, text='Czy problem integracji jest rozwiązany?')
    model = FakeModels()
    Index(store, model, Config()).build('dev')
    evidence = Retriever(store, model).retrieve(q, 'bm25')['evidence']
    obj = {key: [] for key in SECTIONS}
    obj['resolutions'] = [{'text': 'Resolved', 'sources': ['E1'], 'confirmation_quote': quote}]
    assert validate_decision(json.dumps(obj), evidence)[1] is None


def test_target_unit_survives_preceding_context_budget(store):
    from decision_memory.evidence import extract_options
    from conftest import Tokenizer
    turns = [{'turn_id': 'prior', 'role': 'assistant', 'content': 'one two three four five six seven eight nine'},
             {'turn_id': 'target', 'role': 'user', 'content': 'Camera integration is approved and fully resolved.'}]
    full = ''.join(f"{t['role']}: {t['content']}\n" for t in turns)
    start = full.index('user:')
    config = replace(Config(), excerpt_tokens=12, context_tokens=10)
    tokenizer = Tokenizer()
    memory = Memory(store, tokenizer)
    options = extract_options({'question': 'camera integration'}, [0],
                              [{'session_id': 's', 'date': '2023-05-01', 'start': start, 'end': len(full)}],
                              {'s': turns}, tokenizer, config, memory)
    assert turns[1]['content'] in options[0]['text']
    assert len(tokenizer.encode(options[0]['text'])) <= config.excerpt_tokens
    assert options[0]['source_spans'][0]['turn_id'] == 'target'


def test_latest_duplicate_wins_when_only_one_excerpt_fits(store):
    text = 'The camera integration concern is resolved.'
    put_session(store, 'h1', 'older', text, '2023/05/01 (Mon) 10:00')
    put_session(store, 'h1', 'newer', text, '2023/05/29 (Mon) 10:00')
    q = put_question(store, text='What is the latest camera integration state?')
    model = FakeModels()
    config = replace(Config(), max_excerpts=1)
    Index(store, model, config).build('dev')
    evidence = Retriever(store, model, config).retrieve(q, 'bm25')['evidence']
    assert [e['id'] for e in evidence] == ['newer']


def test_latest_plain_fact_duplicate_prefers_newest_without_update_cues(store):
    text = 'The camera lens costs 1000.'
    put_session(store, 'h1', 'older', text, '2023/05/01 (Mon) 10:00')
    put_session(store, 'h1', 'newer', text, '2023/05/29 (Mon) 10:00')
    q = put_question(store, text='What is the latest camera lens price?')
    model = FakeModels()
    config = replace(Config(), max_excerpts=1)
    Index(store, model, config).build('dev')
    retriever = Retriever(store, model, config)
    evidence = retriever.retrieve(q, 'bm25')['evidence']
    assert [e['id'] for e in evidence] == ['newer']
    assert evidence[0]['date'] == '2023/05/29 (Mon) 10:00'
    # Non-temporal questions still follow the original relevance ranking.
    evidence = retriever.retrieve({**q, 'question': 'What is the camera lens price?'}, 'bm25')['evidence']
    assert [e['id'] for e in evidence] == ['older']


def test_latest_plain_fact_does_not_promote_unrelated_newer_wording(store):
    put_session(store, 'h1', 'price', 'The camera lens price costs 1000.', '2023/05/01 (Mon) 10:00')
    put_session(store, 'h1', 'other', 'The camera lens color is blue.', '2023/05/29 (Mon) 10:00')
    q = put_question(store, text='What is the latest camera lens price?')
    model = FakeModels()
    config = replace(Config(), max_excerpts=1)
    Index(store, model, config).build('dev')
    evidence = Retriever(store, model, config).retrieve(q, 'bm25')['evidence']
    assert [e['id'] for e in evidence] == ['price']
