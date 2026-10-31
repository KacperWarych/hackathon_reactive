# Ingestion, indexing, model/configuration audit

Date: 2026-10-31. Researcher model: **gpt-6.1-sol**, reasoning **high**. Independent overseer: `/root/overseer`.

This is the ING group's exhaustive function review of `store.py`, `entries.py`, `chunks.py`, `memory.py`, `index.py`, `models.py`, and `config.py`, plus ingestion tests and setup/dependency sources. It is one part of the whole-pipeline audit; retrieval, answer evaluation, runtime, and UI have other owners.

The active project inspected was `/Users/kacperwarych/Desktop/hackathon reactive ai`. All **38 function definitions** in the seven assigned modules were read. Their names, line ranges, and source hashes are in `ing-source-function-inventory.json`; the function matrix below records evidence and untested areas. No applicable AGENTS.md was found in the checked ancestors or the active source/test trees. No production source or production database was modified. No credentials or `.env` contents were read. All writes were research artifacts or temporary data; no neural weights, paid experiments, or remote APIs were used.

The most actionable defects are inconsistent reimported questions/gold, delayed commits after an ingestion failure, accepted records that cannot be indexed, the manual export/import collision, concurrent indexing failure, and missed sentence boundaries with the real tokenizer. Lower-priority mechanisms, limitations, and hypotheses are explicitly separated rather than counted as production defects.

## Reproduction

From `/Users/kacperwarych/Documents/ChatGPT/hackathon reactive ai`:

```sh
PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
PYTHONPATH='/Users/kacperwarych/Desktop/hackathon reactive ai/src' \
'/Users/kacperwarych/Desktop/hackathon reactive ai/.venv/bin/python' \
outputs/pipeline-research/full-audit-2026-10-31/ing-probes.py

PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
PYTHONPATH='/Users/kacperwarych/Desktop/hackathon reactive ai/src' \
'/Users/kacperwarych/Desktop/hackathon reactive ai/.venv/bin/python' \
outputs/pipeline-research/full-audit-2026-10-31/ing-real-tokenizer-probe.py
```

Outputs: `ing-probe-results.json` and `ing-real-tokenizer-results.json`. The first uses deterministic fake vectors and a whitespace tokenizer to isolate control flow. The second uses the existing local Qwen tokenizer snapshot `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`, with `local_files_only=True`. Neither loads model weights. Concurrency probes use explicit barriers and separate thread-owned database connections; exception-winning thread order may vary.

Existing assigned regression suites were run with `PYTHONDONTWRITEBYTECODE=1`, offline flags, active `src` on `PYTHONPATH`, and `pytest -p no:cacheprovider` against `test_dataset.py`, `test_entries.py`, `test_retrieval.py`, and `test_long_memory.py`: **36 passed in 0.25 seconds**. These synthetic regression tests do not cover the counterexamples below. The overseer independently reran ING-01 through ING-15 and reproduced their observed mechanisms.

Priorities: P1 requires early attention to failure integrity; P2 is a concrete correctness/reliability gap or worthwhile measured mechanism; P3 is a conditional edge case, defensive guard, or unmeasured improvement. Priority is not an observed frequency estimate.

## Confirmed correctness and failure-handling defects

### ING-01 — Reimport can retain questions whose gold labels were removed [P2]

**Code:** `store.py:107–113,127–131`; question rows use `INSERT OR REPLACE`, while gold is replaced as a complete file. `evaluation.py:36–58` subsequently assumes every stored question has a gold entry.

**Evidence:** Probe imports q1/q2 plus corresponding gold, then imports q1-only data/gold into the same split. Stored questions remain `['q1','q2']`; gold contains only `['q1']`. Consumers indexing gold by q2 can raise `KeyError`. This is the inconsistency, not a claim that omitted histories must always be deleted. The README advises retaining the same source files when resuming preparation, which reduces exposure in that documented workflow; the generic importer still accepts changed sources without detecting this condition.

**Fix:** Define explicit merge/replacement modes and keep public questions and gold consistent with the selected mode. For merge, merge validated gold by question ID with source provenance; for replacement, replace the requested scope's questions and gold together. Reject unsupported changed-source reimports before publication.

**Validation:** Reimport shrinking and expanding sources, filtered histories, public-only data, and absent gold. Confirm every evaluation-eligible stored question has the expected annotation, while unrelated partitions and manual additions retain their declared semantics.

### ING-02 — Reimporting exported manual conversations conflicts with preserved rows [P2]

**Code:** `entries.py:48–53`; `store.py:133–150`. Ingestion preserves existing manual session IDs during DELETE, then unconditionally INSERTs source sessions.

**Evidence:** Add a manual conversation, export it, place that exported history in the supported `public/histories.jsonl` location alongside a required `public/questions.jsonl`, and ingest it into the same split/history. Result: `sqlite3.IntegrityError: UNIQUE constraint failed: sessions.split, sessions.history_id, sessions.session_id`. The probe uses a supported dataset directory, not a standalone exported fragment missing required files.

**Fix:** Recognize an incoming session already preserved as manual: accept an identical record idempotently, and define explicit behavior for a conflicting record. Do not silently overwrite a manual addition with unrelated content. Scope the preserved-session reconciliation to the current history transaction.

**Validation:** Export/reimport unchanged manual sessions twice; reimport original data afterward; test same-ID/different-content conflicts; verify original-session and manual-entry counts and content after each step.

### ING-03 — Ingestion accepts records that cannot support indexing/provenance [P2]

**Code:** `store.py:119–150` validates turn role/content but not required `turn_id`; `chunks.py:12` accesses that field unconditionally.

**Evidence:** A turn with role/content but no turn ID imports successfully; lexical index construction then raises `KeyError('turn_id')`. Duplicate turn IDs also import successfully. A question referring to a history absent from the database is accepted. The missing-ID crash is demonstrated; duplicate-ID provenance ambiguity and absent-history answerability are additional validation gaps, not separately measured answer errors.

**Fix:** Validate each record's schema and ID types before changing its persisted scope. Require unique nonempty turn IDs per session, unique session IDs per history, and valid question/history linkage after an import's staged records are reconciled. If missing IDs are a supported input format, generate stable IDs deliberately before hashing and persistence rather than failing later.

**Validation:** Missing, duplicate, empty, wrong-type, and valid IDs; questions preceding histories in tar order; filtered imports; intentionally public-only imports. Invalid input must report the offending record and leave declared committed scope consistent.

### ING-04 — Failed question ingestion leaves a transaction that another operation commits [P1]

**Code:** `store.py:127–131,153`; `memory.py:30–37`. Question inserts have no exception rollback boundary; a later `executescript` publishes their pending transaction.

**Evidence:** The probe imports one valid question followed by an invalid-date question. Ingest raises `ValueError`, but `store.db.in_transaction` remains true. Constructing `Memory` on that connection calls `executescript`; another connection then sees the earlier question `partial`, despite the ingestion operation having failed. This is not an objection to explicit per-history streaming checkpoints; it is a delayed, implicit commit after a failed file-level operation.

**Fix:** Wrap question-file ingestion in an explicit transaction/savepoint and roll it back on failure. Define/report completed per-history checkpoints separately. Schema initialization should not unexpectedly commit unrelated pending application writes; initialize schemas before operational transactions or use explicit migration/transaction ownership.

**Validation:** Fail after at least one valid question, then initialize Memory, run indexing, save an unrelated manual entry, close/reopen, and inspect through an independent connection. Failed question-file inserts must not appear later unless a documented partial-import policy explicitly committed them.

### ING-08 — Concurrent indexing of the same content can fail at the readiness marker [P2]

**Code:** `index.py:41–53`. Readiness is checked before chunk computation; insertion of the marker uses plain `INSERT`.

**Evidence:** Two workers use separate thread-owned SQLite connections and synchronize after both see the content as unindexed. One completes; the other raises `IntegrityError: UNIQUE constraint failed: indexed.content_hash, indexed.scheme`. This is a reproducible concurrent path in the library. No claim is made that a specific existing UI session has already encountered it.

**Fix:** Either serialize builds per database/content/scheme with an explicit lock, or make chunk plus readiness publication idempotent under a transaction that rechecks readiness. If duplicate computation is acceptable, marker insertion may be conflict-tolerant only when chunk completeness is guaranteed. Reconcile concurrent embedding publication too.

**Validation:** Barrier-synchronized lexical and dense builds from separate connections/processes; both should complete or return a controlled already-built result, with one complete chunk/vector set and no partial-ready state.

### ING-16 — Sentence-aware memory splitting misses ordinary period-space boundaries [P2]

**Code:** `memory.py:54–64`. The regular expression records the position *after punctuation plus following whitespace*, then requires exact equality with a tokenizer token's end.

**Evidence with actual tokenizer:** Six 70-word sentences separated by `. ` produce 427 Qwen tokens. The six recorded boundaries are 561,1122,1683,2244,2805,3366; only final3366 matches a token end. Units therefore end after 200/200/27 tokens, with the first two ending mid-sentence even though suitable sentence ends exist. In the newline control, all six boundaries match and units contain 142 tokens each. This is specific to punctuation/whitespace alignment, not a claim that newline boundaries are broken.

**Fix:** Map sentence punctuation ends to token boundaries, or record punctuation-end offsets before whitespace and handle whitespace explicitly in the next span. The probe confirms all six punctuation-end offsets match Qwen token ends in this example. Preserve source offsets and bound the selected units; bump `SCHEME` so cached records are invalidated.

**Validation:** Real-tokenizer tests for `. `, `? `, `! `, newline, Unicode text, and multi-token punctuation; verify useful sentence boundaries are preferred when they lie inside the allowed window, all text remains traceable, and the unit budget is respected. The effect on downstream answer quality remains unmeasured.

## Conditional consistency and input/configuration limitations

### ING-05 — Unknown colon labels have ambiguous speaker attribution [P3; design limitation]

**Code:** `entries.py:21–27`. Unknown labels become continuation text for the prior recognized speaker.

**Evidence:** `Customer: Camera integration blocked.\nManager: Approved the budget.` becomes a single user turn containing the Manager line. This follows the current multiline grammar; it is not proof that every colon line should be interpreted as a new speaker.

**Fix:** Document supported role aliases and surface likely unknown labels for correction or explicit multiline acceptance. A stricter mode may reject unsupported speaker-like labels, with an escaping convention for legitimate colon text.

**Validation:** Known aliases, unknown roles, ordinary `Budget: ...` multiline notes, quoted transcripts, and empty turns. Confirm a user can resolve ambiguity without losing intended content.

### ING-06 — Config permits invalid budgets/batch sizes that fail later [P3; direct-API edge]

**Code:** `config.py:28–47`; `chunks.py:20–24`; `index.py:59`.

**Evidence:** `Config(target_tokens=800,max_tokens=600)` emits a chunk with 802 whitespace tokens because fallback `ideal` is not bounded by `cap`. A zero batch size reaches `range(...,step=0)` and raises a generic `ValueError`. The application defaults do not trigger these examples; no UI exposure is claimed.

**Fix:** Validate relationships and positive batch sizes in `Config.__post_init__`, including `0 < target_tokens <= max_tokens - label_margin`, nonnegative overlap less than effective chunk size, and positive excerpt/message budgets. Also clamp the chunk fallback to `cap` defensively.

**Validation:** Reject impossible configurations at construction with clear messages; test boundary-valid configurations and default chunk-size compliance with the real tokenizer.

### ING-07 — Atomic JSON helper is unsafe for overlapping writers to one path [P3; concurrency limitation]

**Code:** `config.py:18–25`: every writer uses the same `<target>.tmp` filename.

**Evidence:** Two helper callers synchronized at fsync both write the same temp path; one succeeds and the other gets `FileNotFoundError` on replace. This demonstrates the helper's concurrency contract gap. The ING audit has not established that an unlocked production caller actually writes the same target concurrently; upstream locks may cover some paths.

**Fix:** Use a unique temporary file per invocation in the same destination directory, fsync it, replace the target, and clean up only that invocation's temp file. Callers needing read/modify/write consistency also need a path-level lock; unique temp files alone do not solve lost updates.

**Validation:** Concurrent writers must not share temporary paths or fail because another removed their temp file. Test pre-existing target preservation on serialization failure and define expected last-writer behavior separately from state merging.

### ING-09 — Live model-lock changes split runtime identity into old and new revisions [P3; conditional consistency defect]

**Code:** `models.py:30,36–38`; `config.py:50–58`; `index.py:17`.

**Evidence:** Models snapshots revision-A at construction. Editing a temporary lock to revision-B changes `Config.fingerprint` immediately, while `Models.revisions` remains A. No actual model weights are loaded in the probe. The defect requires a lock change while a runtime is alive; documented stable-lock workflows avoid it. Retrieval's fresh lock reads can extend this mismatch to cache labels; that cross-stage risk belongs to overseer/RET review.

**Fix:** Bind one immutable validated revision manifest to a runtime and derive its config, chunk scheme, cache identities, and traces from it. Reject a changed disk manifest until reinitialization, or rebuild the whole runtime atomically.

**Validation:** Change a temporary lock with an existing Models/Index instance; operations must either retain one clearly identified old snapshot or fail with a restart requirement. They must not label old inference with new revisions.

### ING-10 — MPS fallback covers forward execution, not model allocation/loading [P3; recovery limitation]

**Code:** `models.py:48–59,61–76,83–84,105–106`.

**Evidence:** A mock allocation-time `_load` failure with `RuntimeError('MPS out of memory during model allocation')` escapes `embed` and leaves device=`mps`. This proves absent fallback coverage at that stage; it is not a measured failure on the user's device. The README's general fallback description may overstate coverage.

**Fix:** Centralize the load/forward recovery policy, retry supported MPS allocation/runtime failures on CPU, and clear partially initialized state. Avoid retrying malformed model/configuration errors as hardware errors. Alternatively narrow the documented promise.

**Validation:** Mock load-time and forward-time recoverable failures independently; ensure one CPU retry, finite output, compatible dtype, and no loops. Confirm on real hardware only if a representative failure is available without expensive stress tests.

### ING-12 — Explicitly requested missing history IDs silently produce a successful empty build [P3; validation gap]

**Code:** `index.py:34–36` intersects requested IDs with existing histories without checking the difference.

**Evidence:** `build('dev',['does-not-exist'],dense=False)` returns histories=0,sessions=0 without an error. This can conceal a stale manifest; a deliberately empty selection is a different case.

**Fix:** Validate nonempty explicit selections against the available split and report missing IDs, with an explicit allow-missing option if desired.

**Validation:** Mixed valid/invalid IDs, empty list, `histories=None`, absent split, and fully valid manifests. No heavy indexing is needed.

### ING-17 — Tar dataset-file identity is ambiguous and empty archives succeed [P3; input-manifest limitation]

**Code:** `store.py:35–41,115–126,133–150` recognizes members by basename and resets duplicate-row tracking for each member.

**Evidence:** An empty tar imports successfully with zero records. A tar with `one/histories.jsonl` and `two/histories.jsonl`, both naming the same history but distinct sessions, reports histories=2,sessions=2 while retaining only the second session. This is ambiguous-input behavior; partial archives are deliberately used by existing tests, so requiring both public files unconditionally would break a supported test workflow.

**Fix:** Reject duplicate recognized dataset-file identities unless explicit multi-source merge semantics are requested. Distinguish valid partial imports from empty/unrecognized archives; expose the files/scopes processed and warn or fail on an empty import as appropriate.

**Validation:** Single wrapped archive, partial histories-only archive, empty/unrecognized archive, duplicate members, combined-split tar, and duplicate rows across members. Verify reported counts describe processed records clearly and do not masquerade as final database counts.

## Performance mechanisms and defensive improvement hypotheses

### ING-11 — Cached memory records are mutable by callers [P3; hardening hypothesis]

**Code:** `memory.py:42–45,68–71` returns the same cached list/dicts.

**Evidence:** A probe mutates `records[0]['start']`; a second read returns the mutated value. Existing `prepare`/evidence callers inspected do not perform this mutation, so this is not a demonstrated production correctness bug.

**Improvement:** Return immutable records or copies if the API is intended for broader callers; document read-only ownership if avoiding copy overhead.

**Validation:** Mutation cannot affect a subsequent read, or mutation is rejected. Compare overhead before selecting a representation.

### ING-13 — Lexical candidate queries unnecessarily fetch vector BLOBs [P2; confirmed mechanism, impact unmeasured]

**Code:** `index.py:97–110` SELECTs `e.vector` and fetches all rows even when `dense=False`, then discards the BLOB.

**Evidence:** SQLite trace confirms the vector column is selected in lexical mode. The tiny probe has 64 bytes of eligible fake vectors; production default 1,024-dimensional float32 vectors imply 4,096 bytes per eligible chunk before other row payload. That multiplication is a storage-size calculation, not a measured latency/RSS result.

**Improvement:** Use a lexical SQL path omitting the embedding join/vector column. Keep the dense path's explicit missing-vector checks.

**Validation:** Lexical results must match with zero and many existing embeddings. On a controlled temporary corpus measure bytes fetched, peak RSS, and cold/warm query time; do not infer an actual speedup from SELECT inspection alone.

### ING-14 — Index trusts externally supplied or stored vector validity [P3; defense-in-depth hypothesis]

**Code:** `index.py:72–78,103–114` persists/reads vectors without validating dimensions, norms, or finiteness.

**Evidence:** A deliberately nonconforming fake Models producer returns NaNs, which Index accepts. **The actual `Models.embed` already checks finiteness at `models.py:95–97`; this probe bypasses that production guard.** No corrupt production vectors were observed.

**Improvement:** If supporting custom model adapters, shared caches, or storage-integrity checks, validate the interface contract at the Index boundary and retain model dimension metadata. Otherwise document the trusted-producer requirement.

**Validation:** Wrong dimensions, NaNs, truncated BLOBs, zero vectors, and a valid production-shaped vector. Fail clearly before a matrix multiplication or corrupt ranking.

### ING-15 — Cue regexes do not encode negation, assertion identity, or revocation [P3; disclosed design limitation]

**Code:** `memory.py:10–21`.

**Evidence:** `Not approved.` is a confirmation cue; `Unapproved budget.` is a requirement cue; `Approved yesterday, revoked today.` is a confirmation cue. The module and README explicitly call these search hints, not verified states. These results alone are not bugs or measured state errors.

**Improvement:** Keep lexical cues as hints. If downstream code uses them to stop update searches or prioritize current state, separately evaluate assertion scope, negation, and same-entity linkage; RET owns that consequence.

**Validation:** Contrastive cue/state examples with negation, conditionals, old versus revoked approvals, assistant proposals, and different entities. Measure downstream evidence/state errors rather than demanding regexes become a semantic verifier.

### ING-18 — Identical uncached texts within one embedding batch are encoded repeatedly [P3; confirmed wasted-work mechanism]

**Code:** `index.py:63–80` checks persistent text-cache entries for all missing rows before publishing that batch. Duplicate fresh texts within the batch all remain in `fresh`.

**Evidence:** A single repetitive 2,200-word session results in six submitted fake embedding documents, but only three distinct strings. This demonstrates redundant work; actual neural runtime savings are unmeasured. Cross-batch and later-build reuse still work.

**Improvement:** Deduplicate fresh text hashes within each batch, encode unique texts, then bind each result to all corresponding chunk IDs. Keep source IDs/offsets distinct.

**Validation:** Repetitive and unique chunks, duplicates across sources, later append reuse, and output equality. Count actual adapter calls and encoded tokens; benchmark weights only in a separately authorized experiment.

### ING-19 — Replaced source revisions and derived caches accumulate without a lifecycle [P3; storage-design limitation]

**Code:** `store.py:134–148`; `index.py:48–80`; `memory.py:65–67`. Reimport replaces session references but does not reclaim unreferenced content/chunks/embeddings/memory records.

**Evidence:** The small probe leaves three content rows no longer referenced by any session after ordinary replacement/reindex operations. Caching old revisions may be intentional, especially for shared content; no disk exhaustion or inappropriate retention was observed.

**Improvement:** Provide retention accounting and an explicit garbage-collection command with a dry run and reference tracing across all splits, active runs, and text-cache links. Do not delete shared content merely because one history changed.

**Validation:** Orphan versus shared revisions, saved-run provenance requirements, interrupted cleanup, and text-cache foreign references. Measure retained disk size before deciding a policy.

### ING-20 — Public customer/call identity metadata is discarded during ingestion [P2; source-contract design limitation]

**Code:** `store.py:53–55,137–150`; `Store.sessions:86–89` returns the stored session plus turns but cannot restore omitted source metadata. [Dataset README:23](/Users/kacperwarych/Desktop/hackathon%20reactive%20ai/salesgen_dataset_fail/README.md:23) declares public `meta.call_id`, `customer_id`, `customer_name`, and `product_id`; [README:69](/Users/kacperwarych/Desktop/hackathon%20reactive%20ai/salesgen_dataset_fail/README.md:69) says aggregate questions count customers once, using the reason from their latest call.

**Independent evidence:** `ing20-metadata-probe.py` reads only the public histories/questions and README, then imports the public directory into a temporary database. It confirms **176 calls, 147 distinct customer IDs, and 29 customers with multiple calls**. All four metadata fields occur in all 176 source sessions. The imported database returns 176 sessions with **zero `meta` fields**; its session schema has only split/history/session/date/ISO/position/content hash, while content payloads contain turns only. Results are in `ing20-metadata-results.json`. No production or evaluation-gold database/file was used by this probe.

The public IDs are therefore unavailable to a downstream workflow operating on the stored records. This prevents authoritative key-based customer deduplication and product/call linkage from those records; text-based identity inference is a possible but unverified fallback, not an equivalent preservation of the supplied IDs. It is the ingestion counterpart to RET-05's missing complete-coverage aggregation route. More excerpts alone cannot restore discarded source fields. This is classified as a design limitation relative to the supported salesgen contract, not a claim that the original challenge schema required these extensions.

**Fix:** Introduce a versioned SQLite/import schema preserving session source metadata separately from evaluation annotations, preferably validated typed call/customer/product fields plus an original-source metadata payload for traceability. Bind metadata to split/history/session, not to shared turn-content hashes: identical text can belong to different customers or calls. Reimport the public source to populate existing records and expose the identity fields to retrieval/aggregation/export paths. Missing metadata must stay unknown rather than inventing customer IDs. Preserve separation from `calls_gold.jsonl`: outcome, reason, fault, and similar labels are evaluation-only and must never enter retrieval or extraction inputs.

**Validation:** Round-trip all four public fields for 176 source sessions; repeated same-customer calls must remain distinct calls but form one customer group. Select the latest eligible call at the question's as-of date, apply product scope according to the actual question, handle equal/missing timestamps explicitly, and verify grouping/aggregation on small public-like examples with changing reasons. Confirm no outcome/reason labels are present in ingested retrieval records. Compare downstream counts against evaluation-only labels only in the evaluation process, never by ingesting them as evidence.

## Every-function coverage matrix

All rows were inspected in source. “Regression” means exercised by the existing assigned suites, not proof of complete branch coverage. No blanket claim of model-runtime validation is made.

| Function / start line | Evidence examined / outcome |
| --- | --- |
| store.iso_date:12 | Date regression and invalid-date probe; supported formats parsed; timezone/locale extensions out of scope. |
| store.dataset_files:21 | Directory/archive regression, partial archive, empty/duplicate tar probes; ING-17. |
| Store.__init__:45 | Temporary independent WAL connections, schema and transaction inspection; ING-04/08/20; no production DB opened. |
| Store.close:73 | Temporary store close/reopen and independent connection checks; no separate defect found. |
| Store.questions:76 | ID selection validation regression; reimport probe demonstrates stale rows (ING-01); full-split materialization is a potential scaling cost, unbenchmarked. |
| Store.sessions:86 | Idempotence, history-specific metadata, manual roundtrip regressions; ING-20 public identity omission; all sessions/turns per selected history materialized during build, unbenchmarked. |
| Store.stats:91 | Directory ingestion regression and probe setup; source counts versus final counts distinguished; no separate defect. |
| Store.valid_sessions:95 | Entry isolation and absent-history probes; no separate SQL isolation defect found. |
| Store.ingest:99 | ING-01/02/03/04/17/19/20; source-scoped replacement semantics and failure paths inspected. |
| entries.parse_transcript:12 | Alias/multiline/empty validation regressions and ING-05. |
| entries.add_entry:33 | Persistence, idempotence, date/history validation and original reimport regression; ING-02 consequence. |
| entries.export_entries:48 | Manual export source reconstructed as valid dataset directory; ING-02. |
| chunks.chunk_turns:6 | Coverage/overlap/role regression and config probe; ING-03/06; default real-tokenizer exhaustive property check not run. |
| chunks.chunk_scheme:39 | Tokenizer revision and geometry inputs inspected; source-changing algorithms require manual version bump; no independent collision defect observed. |
| memory.cues:20 | English/Polish regression and contrastive examples; ING-15 disclosed lexical limitation. |
| Memory.__init__:25 | Transaction-publication probe ING-04 and tokenizer-key scheme inspection. |
| Memory.records:39 | Incremental source rebinding regression, mutability probe ING-11, actual-tokenizer sentence probe ING-16. |
| Memory.prepare:73 | Index/repeated-turn regression, forwards records without mutating results; no separate defect. |
| Memory.inference_get:77 | Persistent cross-retriever cache regression and counter handling inspection; no separate defect. |
| Memory.inference_put:86 | Cache reuse regression; 8,192-row cap inspected; eviction is insertion-row based, not access LRU, a policy choice not benchmarked here. |
| Index.__init__:15 | Revision/scheme snapshot inspected; ING-09 conditional manifest consistency. |
| Index.build:19 | Idempotence, incremental reuse, missing-ID and parallel barriers; ING-03/06/08/12/18/19. |
| Index.candidates:90 | Time/history isolation and missing-index regression; lexical trace ING-13 and optional adapter-contract probe ING-14. |
| models.setup_models:13 | Lock creation/download allow-list read; no HfApi, download, or installer executed. Missing-lock `download=False` can still resolve revision metadata by design; no offline guarantee assumed. |
| Models.__init__:27 | Temporary-lock/mocked-device construction ING-09; no weights. |
| Models.key:36 | Pinned embedding revision/pooling identity read; conditional disk-lock mismatch ING-09; backend numerical reproducibility not measured. |
| Models.tokenizer:41 | Lazy pinned left-padding construction read; independent actual local tokenizer loaded for ING-16; online fallback behavior not exercised. |
| Models._load:48 | Dtype, device, architecture, eval mode and rerank tokenizer read; no weights; ING-10 coverage gap. |
| Models._forward:61 | Inference-mode forward and CPU recovery paths inspected; actual MPS/CUDA/CPU inference not run; ING-10. |
| Models.embed:78 | Instruction formatting, last-token pooling, normalization, lengths and finite guard read; mock load-error probe; no vector-quality or real-forward measurement. |
| Models.rerank:100 | Qwen yes/no prompt, logits difference, length/finite checks read; no inference or score calibration claim. |
| config.digest:14 | Canonical sorted JSON hashing used throughout probes; no independent collision/error found. |
| config.atomic_json:18 | Fixed-temp concurrency barrier ING-07; single-writer fsync/replace source inspected. |
| Config.fingerprint:50 | Temporary-lock snapshot discrepancy ING-09; runtime/environment fingerprint scope inspected; no extra finding. |
| config.revisions:54 | Missing-file error and JSON read source inspected; temporary lock revisions exercised; schema validation is limited to consumers. |
| config.data_root:61 | Temporary path creation and environment setup exercised; HF_HOME is set only if absent, so it can intentionally remain distinct from later data roots. |
| config.load_env:69 | Source-only review of dotenv loading with override=False; deliberately did not read the production .env. |
| config.device:74 | MPS→CUDA→CPU precedence and environment override inspected; choice mocked during probes; actual device health not stress-tested. |

Setup/dependency review found Python and model lock files in place. The bootstrap script selects uv without an explicit version and Python by minor version; environment-version recording is a reproducibility improvement, not an additional defect ID or a vulnerability finding. No bootstrap installer or dependency upgrade was executed.

Additional inspected sources: all ingestion/entry/retrieval/long-memory test definitions and fixtures; `scripts/setup.sh`; `scripts/prepare.py.main:15`; `pyproject.toml`; `uv.lock`; `models.lock.json`; relevant README/implementation contracts. `prepare.main` sequencing, resumability, import ordering, and dependency setup were read; the full heavyweight preparation workflow was not executed. The group does not claim to have exhaustively reviewed unassigned runtime/UI/evaluation functions.

## Independent critique and explicit revisions

The overseer challenged broad claims based on synthetic probes and requested contract-sensitive classifications. **Accepted and revised:** ING-01 concerns stored-question/gold inconsistency rather than assuming all omitted histories should disappear; ING-02 uses a supported directory with questions present; ING-05 is grammar ambiguity; ING-06 is a lower-priority direct-Config edge case; ING-07 is a helper concurrency limitation unless an actual unprotected caller is established; ING-08 has independent connections and an explicit barrier; ING-09 is conditional on live lock changes; ING-10 is mock-only recovery coverage; ING-11 and ING-14 are hardening hypotheses; ING-15 is a disclosed lexical hint limitation; ING-13 and ING-18 establish wasted-work mechanisms, not measured latency improvements. The independent rerun reproduced ING-01–15. ING-16's reproducible real-tokenizer script now includes a newline control and a punctuation-end alignment check.

The parent subsequently identified the salesgen customer-versus-call contract. Independent public-only verification confirmed ING-20. The classification remains a source-contract design limitation; the remedy preserves authoritative public metadata and keeps call-level outcome/reason gold strictly in evaluation. No other new candidate IDs were added in this follow-up.

## Remaining uncertainty and next experiments

No production failure prevalence, end-to-end answer accuracy, model-ranking comparison, memory-pressure event, GPU performance, or dependency vulnerability assessment was measured. The corpus-wide impact of missed sentence boundaries, data-source changes in normal use, same-target concurrent writers, and long-lived cache growth remains unknown. Current default model inference already includes finite checks and follows the inspected Qwen-specific pooling/reranking design; the audit provides no basis for claiming an alternative model is better.

The cheapest high-value next steps are: fix ingestion transaction/annotation consistency and add targeted negative-input regressions; use real-tokenizer span retention checks for sentence splitting; exercise synchronized index publication; then benchmark the two demonstrated redundant-work paths independently with fixed corpus, budgets, model revision, and cold/warm-cache conditions. Any whole-pipeline answer experiment should reuse the separate assertion-retention diagnostic proposed in the first-cycle report and preserve official session-level scoring.
