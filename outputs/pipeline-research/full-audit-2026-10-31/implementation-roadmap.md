# Proposed fix order and validation gates

Research recommendations only. This audit did not modify the application or establish the answer-quality gain of a proposed replacement. Keep each change reviewable and validate it before combining changes.

## 1. Make the executable match the reviewed source

First resolve RUN-06: rebuild/reinstall the intended frozen package using the repository's documented command, restart the app, and verify source/installed hashes. Run the normal-import UI test for Build decision view and the new entry-in-report flow. Add a build/import smoke check so future source-only passing tests cannot hide stale installed code.

**Gate:** the intended app imports the intended package revision; installed and source smoke tests agree. Record package/model/code versions in every benchmark and report.

## 2. Protect corpus identity and transactional imports

Preserve allowlisted public customer/product/call metadata from Salesgen; keep gold outcome labels evaluation-only. Validate file layout, required fields, dates, roles and turn IDs before publishing an imported dataset revision. Define import mode explicitly: complete replacement, history-scoped replacement or append. Replace questions, sessions and evaluation gold consistently. Preserve manual entries with idempotent collision handling and ensure manual export can be reimported. Roll back failures rather than leaving pending SQL statements to a later schema initialization. Serialize or safely upsert concurrent index work and give JSON writers distinct temporary files.

**Gate:** malformed late records, duplicate archive members, removed questions, manual-export round trips and concurrent writers cannot publish a mixed or misleadingly successful corpus. Every successful import has a dataset revision that downstream artifacts can bind to.

## 3. Preserve source facts and speaker provenance

Fix answer loss in evidence construction before changing encoders: preserve the selected target unit when adding context; nominate more than two eligible units under a bounded policy; remove overlap only when the dropped span contributes no needed unique text; distinguish repeated assertions across dates; map sentence boundaries correctly to real tokenizer offsets. Carry role, turn ID, character offsets, source hash and date as structured metadata. Never infer authoritative role boundaries from strings inside speaker content.

**Gate:** existing and new real-tokenizer counterexamples retain target assertions; assistant text containing `user:` cannot become user evidence; negation and nearby context survive; chronological repeated assertions keep relevant dates. Hold final evidence budgets fixed while comparing remedies.

## 4. Make reuse and completion claims traceable

Bind indexes, cached evaluations, frozen selections, runs, reports and exports to code/model/tokenizer/query/gold/source revisions. Separate an immutable historical snapshot from an answer against current data. Reject incompatible resumes without automatically resending requests. Validate exact benchmark manifests and stage completion at the live-run/export gate. Keep decisions generated from saved evidence labeled with that saved snapshot rather than relabeling them as current source state.

**Gate:** changing content under a stable session ID, question text, gold, date, lockfile or code revision invalidates the relevant current-data reuse; unchanged inputs resume without duplicate computation or remote calls.

## 5. Repair retrieval control flow and durable recovery

Ensure update-search budget is spent on genuinely new candidates, not old initial candidates that missed reranking. Review tiny-corpus BM25 behavior, query expansion language, and completeness gates using labeled cases. Persist entry indexing/refresh state across browser sessions. Restore failed revision inputs from the journal. Preserve all evidence constraints in correction prompts, validate answer content after citation stripping, and add a parent process deadline with an explicit uncertain-outcome state.

**Gate:** new expansion candidates can enter final ranking; recovery repeats the intended operation exactly; a browser restart retains retry controls; citation-only output cannot count as a completed answer; an uncertain transport outcome is never blindly retried.

## 6. Rebuild trustworthy evaluation, then choose alternatives

Strip citation labels before local answer matching while preserving official scoring semantics. Keep session metrics and add a frozen, human-reviewed assertion/span/state set across histories: paraphrase, late assertion, short response, multilingual confirmation, negation, entity mismatch, temporal update and repeated text. Use the available evaluation-only call labels as an audited classification diagnostic and add human span annotations. Include a separate complete-enumeration track for aggregation questions; top-k evidence cannot certify full-population totals.

Compare the current stack with cheaper bounded fixes first. Then perform matched BM25/dense/hybrid/rerank/update ablations and only then compare Qwen, BGE or contextual embedding alternatives on identical data, candidates and budgets. Select on supported answer quality and coverage constraints, then latency/memory/cost. No alternative model is established as the winner by this audit.

**Gate:** cached reports reflect current inputs; numeric citations cannot create false automatic matches; incomplete runs have explicit denominators; cold/warm timings are separated, order counterbalanced and samples fixed. Report paired uncertainty and measured effects instead of reviewer grades as if they were benchmark gains.

## 7. Optimize after correctness is protected

Avoid loading vector blobs for lexical-only queries, deduplicate pending identical embedding work, avoid extracting every turn in a long session for one retrieved chunk when cached offsets suffice, make stage timings non-overlapping or clearly nested, and plan retention/garbage collection for unreferenced cached content. Add defensive config/vector validation and test supported device fallback paths. Link compatible benchmark snapshots rather than duplicating unrelated aggregate rows into every report.

**Gate:** output quality stays unchanged under the frozen diagnostic set while representative latency/memory/storage measurements improve. Preserve historical provenance when pruning caches or old source revisions.

## Definition of audit completion

For this source snapshot: every application/vendor Python module, preparation/evaluation/live script and UI composition function is assigned and reviewed; supporting setup/configuration and installed-package differences are inspected; all proposed findings receive independent review and an evidence classification; concrete fixes and acceptance checks are recorded. This is complete coverage of the inspected implementation, not a proof that no additional defect can emerge under untested data, hardware, concurrency or remote-service behavior.
