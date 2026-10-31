"""Offline audit probes. Uses temporary databases and fake transport; no production writes."""
import json
import os
import sys
import tempfile
from contextlib import nullcontext
from pathlib import Path

PROJECT = Path('/Users/kacperwarych/Desktop/hackathon reactive ai')
sys.path.insert(0, str(PROJECT / 'src'))
sys.path.insert(0, str(PROJECT / 'tests'))
from conftest import FakeModels, put_question, put_session
from decision_memory.config import Config, atomic_json
from decision_memory.evaluation import evaluate_answers, evaluate_retrieval
from decision_memory.index import Index
from decision_memory.reactor import checked_result, citation_repair_question, export_predictions, result_path, run_questions
from decision_memory.retrieval import Retriever, reactor_question
from decision_memory.store import Store, iso_date
from decision_memory.vendor.reactor_client import parse_question_date
from decision_memory.vendor.score import answer_matched


class Adapter:
    agent_key = 'audit-fake-agent'
    def __init__(self):
        self.calls = []
    def lock(self):
        return nullcontext()
    def call(self, *args):
        self.calls.append(args)
        if args[0] == '--new-history':
            return {'status': 'history', 'history_id': 'audit-h1'}
        return {'status': 'answered', 'answer': 'The budget is approved [E1].',
                'abstained': False, 'citations': [{'label': 'E1', 'id': 's1'}]}


def main():
    findings = {}
    with tempfile.TemporaryDirectory(prefix='pipeline-runtime-audit-') as directory:
        root = Path(directory)
        os.environ['MEMORY_DATA_DIR'] = directory
        store = Store()
        put_session(store, 'h1', 's1', 'The budget is approved.')
        q = put_question(store, text='Is the budget approved?')
        models = FakeModels()
        Index(store, models, Config()).build('dev')
        adapter = Adapter()
        run_questions(store, Retriever(store, models), [q], 'stale', 'bm25', adapter=adapter)
        before = len(adapter.calls)
        put_session(store, 'h1', 's1', 'The budget is NOT approved.')
        run_questions(store, Retriever(store, models), [q], 'stale', 'bm25', adapter=adapter)
        exported = export_predictions(store, 'stale', root / 'export.jsonl')
        findings['RUN-01'] = {'additional_calls_after_source_change': len(adapter.calls)-before,
                              'export': exported, 'prediction': json.loads((root/'export.jsonl').read_text())}

        annotation = {'question_id': q['question_id'], 'question_type': 'single-session-user',
                      'abstain': False, 'answer': '1', 'evidence': ['s1']}
        gold_path = root / 'evaluation' / 'gold-dev.jsonl'
        gold_path.parent.mkdir(exist_ok=True)
        gold_path.write_text(json.dumps(annotation)+'\n')
        run = root / 'runs' / 'numeric'
        atomic_json(run / 'run.json', {'split': 'dev', 'question_ids': [q['question_id']]})
        atomic_json(result_path(run, q['question_id']), {'result': {
            'status': 'answered', 'answer': 'The budget is approved [E1].', 'abstained': False,
            'citations': [{'id': 's1'}]}})
        findings['RUN-03'] = evaluate_answers(store, 'numeric')['judgments']
        findings['RUN-03']['without_citation_matches'] = answer_matched('The budget is approved.', annotation)

        class CountingRetriever:
            config = Config()
            def __init__(self):
                self.calls = 0
            def retrieve(self, question, mode):
                self.calls += 1
                return {'question': question, 'evidence': [{'id': 's1', 'text': 'old'}],
                        'trace': {'candidates': [{'session_id': 's1'}], 'seconds': 1, 'message_chars': 10}}
        retriever = CountingRetriever()
        manifest = {'name': 'audit', 'split': 'dev', 'question_ids': [q['question_id']]}
        first = evaluate_retrieval(store, retriever, manifest, ['bm25'])
        annotation['evidence'] = ['changed_gold_source']
        gold_path.write_text(json.dumps(annotation)+'\n')
        store.db.execute('UPDATE questions SET question=? WHERE question_id=?', ('A different question?', q['question_id']))
        store.db.commit()
        second = evaluate_retrieval(store, retriever, manifest, ['bm25'])
        findings['RUN-02'] = {'retrieval_calls_across_two_runs': retriever.calls,
                              'same_report': first['path'] == second['path'],
                              'packed_recall_after_changed_question_and_gold': second['summary']['bm25']['packed_recall']}

        question = 'How many customers approved the budget?'
        findings['RUN-04'] = {'initial_has_coverage_constraint': 'complete population coverage' in reactor_question(question),
                              'repair_has_coverage_constraint': 'complete population coverage' in citation_repair_question(question),
                              'initial_has_same_fact_constraint': 'same fact' in reactor_question(question),
                              'repair_has_same_fact_constraint': 'same fact' in citation_repair_question(question)}
        bad_weekday = '2023/05/20 (Mon) 10:00'
        try:
            parse_question_date(bad_weekday)
            vendor_status = 'accepted'
        except ValueError:
            vendor_status = 'rejected'
        findings['RUN-05'] = {'store_parse': iso_date(bad_weekday), 'transport_parse': vendor_status}

        cite_only = {'status': 'answered', 'answer': '[E1]', 'abstained': False,
                     'citations': [{'label': 'E1', 'id': 's1'}]}
        cite_run = root / 'runs' / 'cite-only'
        atomic_json(cite_run / 'run.json', {'split': 'dev', 'question_ids': [q['question_id']]})
        atomic_json(result_path(cite_run, q['question_id']), {'result': cite_only,
                    'retrieval': {'evidence': [{'id': 's1'}]}})
        export = export_predictions(store, 'cite-only', root/'cite-only.jsonl')
        findings['RUN-08'] = {'checked_status': checked_result(cite_only, q, [{'id': 's1'}], store)['status'],
                              'export_complete': export['complete'],
                              'exported_answer': json.loads((root/'cite-only.jsonl').read_text())['answer']}
        store.close()
    (Path(__file__).parent / 'probe-results.json').write_text(json.dumps(findings, indent=2)+'\n')
    print(json.dumps(findings, indent=2))


if __name__ == '__main__':
    main()
