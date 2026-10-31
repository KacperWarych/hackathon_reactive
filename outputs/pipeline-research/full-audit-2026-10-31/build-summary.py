"""Build the readable audit index from the independently reviewed register."""
import collections
import json
from pathlib import Path

root = Path(__file__).resolve().parent
findings = json.loads((root / 'findings.json').read_text())
accepted = [f for f in findings if f['disposition'] == 'accepted']
counts = collections.Counter(f['classification'] for f in accepted)
labels = {'confirmed_bug': 'Confirmed bug', 'limitation': 'Limitation/tradeoff', 'hypothesis': 'Untested improvement'}
link = lambda name, title: f'[{title}](<{root / name}>)'
text = f'''# Whole-pipeline audit — 31 October 2026

The reviewed register contains **{len(accepted)} distinct findings and improvement proposals**: **{counts['confirmed_bug']} confirmed bugs**, **{counts['limitation']} limitations/tradeoffs**, and **{counts['hypothesis']} untested improvement hypotheses**. There are {len(findings)} IDs; merged IDs are retained for traceability and are not counted twice. A confirmed counterexample establishes a possible defect, not its frequency on real conversations. Suggested benefit grades are reviewer judgments, not measured gains.

## Scope completed

Reviewed the active project `/Users/kacperwarych/Desktop/hackathon reactive ai`: all **25 application/vendor/script Python files and 139 function definitions**, including nested helpers; setup and package/Streamlit configuration; dataset format/scoring contracts; and the normal installed package. The initial inventory counted 136 functions; full recursion added three already-reviewed nested helpers. The source hashes were checked for drift before delivery. The separate Salesgen scorer is identical to the vendored scorer.

Pipeline coverage: import/schema/transactions → manual entries and source identity → chunking/memory → embeddings/index/cache → lexical/dense search/fusion/reranking → update search → evidence packing/provenance → Reactor answer generation → structured decisions and report revisions → UI/recovery → evaluation/selection → export/deployment.

Two GPT-6.1 Sol researchers (high reasoning) investigated ingestion/indexing and retrieval/evidence; the lead audited runtime/evaluation/UI/delivery. A GPT-6 Astra overseer (high reasoning) independently checked the evidence, challenged claims, obtained revisions and graded every entry. Models are dispatch metadata; no independent runtime model introspection is available.

## Fix these first

1. **Repair the installed/source mismatch (RUN-06).** The actual installed UI fails `Build decision view` because it rejects `decision_only`; refresh the intended installation, restart, and test the installed artifact.
2. **Make ingestion failures and revisions consistent (ING-01/03/04).** Validate inputs before publication, roll back failed question imports, and reconcile stored questions with their annotations under explicit replacement/merge rules.
3. **Preserve trustworthy identity and provenance (ING-20, RET-06/17).** Keep public customer/product/call metadata, validate speakers from structured source turns, and pack evidence from the same immutable source revision that was ranked.
4. **Stop dropping answer-bearing text (RET-01/02/03/04).** Reserve space for the chosen assertion, broaden unit admission carefully, preserve distinct dates/events, and retain novel text when removing overlap.
5. **Invalidate stale results and benchmarks (RUN-01/02, RET-12).** Bind corpus, question, gold, model and build revisions to all reusable artifacts; retain historical snapshots explicitly instead of treating them as current.
6. **Fix evaluation and completion checks (RUN-03/08/11).** Strip citation labels before answer matching, reject citation-only answers, and validate exact benchmark identity before declaring submission readiness.
7. **Add complete-coverage aggregation and extraction diagnostics (RET-05, RUN-10).** Count latest outcomes per authoritative customer ID where required; use evaluation-only call labels plus independently reviewed spans/state transitions. Keep gold out of retrieval.

The full fix sequence and acceptance gates are in {link('implementation-roadmap.md', 'the implementation roadmap')}. Establish these correctness gates before spending effort on a larger embedding/reranking model. This audit does not establish that Qwen, BGE, contextual embeddings or any replacement is the best-performing choice on this project.

## Verification and limitations

- Full current-source regression suite: **88 passed** with offline settings and temporary test data.
- Normal installed-package UI check: **1 failed**, reproducing the `decision_only` mismatch; independently reproduced by the overseer.
- New temporary-data probes reproduce import, concurrent-write, provenance, stale-cache, evidence-loss and output-validation mechanisms. Selected extraction cases also use the actual cached Qwen tokenizer, without loading neural weights.
- Fresh browser-session recovery probe reproduces lost retry controls after an entry indexing failure.
- Salesgen inspection: 176 public sessions, 147 customer IDs, 59 questions; all sessions carry customer/product/call metadata that ingestion currently discards. No gold source was after its question cutoff. 13/59 questions have more than six gold source sessions; that is a coverage ceiling, not an answer-error rate.
- A historical saved-output check found no citation-only numeric match or empty-answer occurrence among the small inspected sample (21 answered records, 14 answerable scored records, potentially repeated questions). Those defects are controlled counterexamples, not claimed observed production prevalence.
- No application code was changed, remote Reactor calls made, model weights downloaded, or measured remedy gains claimed. Remote-service reliability, actual neural quality, hardware pressure, production-scale concurrency and complete natural-data span accuracy remain unmeasured.

## Complete reviewed register

Grades are **evidence / fit / expected benefit / feasibility**, each 0–5. Evidence grades support the diagnosis; benefit grades express an expected value to test. P1 = early corrective work, P2 = important follow-up, P3 = lower-priority hardening/experiment. A P1 limitation is not automatically a bug. Open a linked group report for exact code references, reproduction, caveats and acceptance tests.

| ID | Priority | Classification | Finding | Proposed solution | Grades |
|---|---|---|---|---|---|
'''
for f in findings:
    grades = '/'.join(str(f[k]) for k in ('evidence_grade','fit_grade','benefit_grade','feasibility_grade'))
    title = f['title'].replace('|', '\\|')
    fix = f['brief_fix'].replace('|', '\\|')
    classification = labels[f['classification']]
    if f['disposition'] != 'accepted':
        classification += ' — ' + f['disposition']
    text += f"| {link(f['group_report'],f['id'])} | {f['severity']} | {classification} | {title} | {fix} | {grades} |\n"
text += f'''
## Detailed evidence and ongoing work

- {link('ing-report.md', 'Ingestion, storage, chunking, indexing, models and configuration report')}
- {link('retrieval/report.md', 'Retrieval, evidence, provenance, decisions and investigation report')}
- {link('runtime/report.md', 'Runtime, evaluation, UI, export and installed-package report')}
- {link('review.md', 'Independent overseer review and grading rationale')}
- {link('findings.json', 'Machine-readable reviewed register')}
- {link('source-function-inventory.json', 'Hashed source and function coverage inventory')}

The daily 09:00 Europe/Warsaw research loop now uses this whole-pipeline audit and backlog, checks changed code and unresolved experiments, and reports meaningful new findings instead of repeating this register. Completion here means all inspected implementation stages have been analyzed and recommendations recorded; it is not a proof that no further defect can emerge under untested conditions.
'''
(root/'AUDIT.md').write_text(text)
print(json.dumps({'distinct_findings':len(accepted),'ids':len(findings),'classifications':dict(counts),'report':str(root/'AUDIT.md')},indent=2))
