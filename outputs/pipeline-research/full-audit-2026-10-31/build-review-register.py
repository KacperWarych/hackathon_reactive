"""Materialize the independent review register; no application code is changed."""
import json
from pathlib import Path
root=Path(__file__).parent
# id, title, classification, severity, evidence/fit/benefit/feasibility, fix
rows=[
('ING-01','Reimport retains obsolete questions while replacing gold','confirmed_bug','P2',(5,5,4,4),'Define merge/replace import semantics; reconcile questions and annotations atomically within the chosen scope.'),
('ING-02','Manual-entry export cannot be idempotently reimported into its history','confirmed_bug','P2',(5,5,3,4),'Reconcile matching manual session IDs without unconditional conflicting INSERT; preserve provenance and reject conflicting content explicitly.'),
('ING-03','Ingestion accepts missing turn IDs and invalid references','confirmed_bug','P2',(5,5,4,4),'Validate schema, unique turn/session IDs and question-history references before publishing an import; allow intentional partial imports only explicitly.'),
('ING-04','Failed question ingestion leaves writes that a later operation commits','confirmed_bug','P1',(5,5,5,4),'Use an explicit import transaction/staging boundary with rollback on every parse/validation failure; publish gold consistently.'),
('ING-05','Unknown speaker labels silently become prior-speaker text','limitation','P3',(4,4,3,4),'Specify transcript grammar and preview parsed speaker attribution; reject or warn about ambiguous unsupported speaker labels without rejecting ordinary colon-bearing prose.'),
('ING-06','Invalid Config values can violate chunk caps or crash indexing','limitation','P3',(5,4,3,5),'Validate positive batch/budget values and target/maximum/overlap invariants at configuration construction.'),
('ING-07','Concurrent atomic_json writers share one temporary filename','limitation','P3',(5,4,4,5),'Use unique same-directory temporary files and atomic replacement; separately lock read-modify-write state that needs serialization.'),
('ING-08','Concurrent index builders race on the indexed readiness marker','confirmed_bug','P2',(5,5,4,4),'Serialize or transactionally claim content/scheme indexing work and make readiness publication idempotent.'),
('ING-09','Live lock-file changes mislabel an existing Models snapshot','confirmed_bug','P3',(4,4,3,4),'Bind model/cache/config provenance to one immutable loaded revision snapshot; reject or explicitly reload after lock changes.'),
('ING-10','MPS recovery covers forward execution but not model allocation','limitation','P3',(3,4,3,3),'Extend tested recoverable-device handling to model load/allocation with clear cleanup and uncertain resource-state handling; validate on real hardware before reliability claims.'),
('ING-11','Memory.records exposes mutable cached objects','hypothesis','P3',(3,3,2,4),'Return immutable records or defensive copies if callers may mutate them; current production callers do not demonstrate this corruption.'),
('ING-12','Unknown requested index histories silently produce zero work','limitation','P3',(4,4,3,5),'Report missing requested history IDs and require explicit allow-missing behavior for a deliberate empty selection.'),
('ING-13','Lexical retrieval fetches unused embedding BLOBs','hypothesis','P2',(5,5,3,5),'Use a lexical SQL projection without vector join/BLOB materialization; benchmark memory and latency before claiming gains.'),
('ING-14','Index boundary trusts vector integrity','hypothesis','P3',(3,3,2,4),'Consider dimensions/finite validation when loading untrusted or migrated vectors; production Models.embed already rejects nonfinite outputs.'),
('ING-15','Lexical cue labels do not resolve negation or fact identity','limitation','P3',(5,4,3,3),'Keep cues as retrieval hints; assess downstream gating against labeled negation/entity/state examples, consolidated under RET-09.'),
('ING-16','Sentence boundaries after spaces do not match real tokenizer offsets','confirmed_bug','P2',(5,5,4,4),'Map punctuation/newline boundaries to valid token ends without consuming following spaces; version memory schema and verify spans.'),
('ING-17','Archive basename/manifest ambiguity permits silent overwrite or empty success','limitation','P3',(5,4,3,4),'Validate declared archive members and duplicate basenames; expose an explicit partial-import mode rather than accepting ambiguous manifests.'),
('ING-18','Repeated uncached texts in one batch are embedded repeatedly','hypothesis','P3',(5,4,3,4),'Deduplicate fresh texts within each model batch and scatter vectors back to chunk IDs; measure work and runtime separately.'),
('ING-19','Old source/index/cache objects have no explicit retention lifecycle','limitation','P3',(4,4,3,3),'Define audit-snapshot/cache retention and reference-aware cleanup; do not delete immutable sources still referenced by reports.'),
('ING-20','Import discards authoritative public customer/call/product metadata','limitation','P1',(5,5,5,4),'Preserve validated public session metadata and stable customer/product identity in storage and snapshot provenance; keep evaluation-only outcome labels out of retrieval.'),
('RET-01','Previous-turn context can clip the selected tail assertion at the default cap','confirmed_bug','P1',(5,5,5,4),'Build context as disjoint bounded spans around the selected unit; preserve the target before truncating context.'),
('RET-02','Lexical top-two unit selection drops relevant paraphrases','limitation','P1',(5,5,5,4),'Generate a broader bounded unit pool and compare relevance/facet selection at a fixed evidence budget; protect answer-bearing units.'),
('RET-03','Text-only deduplication removes distinct later events and dates','confirmed_bug','P1',(5,5,4,4),'Include event/source/time identity in redundancy decisions for temporal questions; retain chronology or merge provenance explicitly.'),
('RET-04','Overlap deduplication drops a short chunk containing novel tail evidence','limitation','P2',(5,5,4,4),'Deduplicate only when unique non-overlapping evidence is preserved; merge spans or retain the novel tail under the budget.'),
('RET-05','Six excerpts cannot cover arbitrarily many required source sessions','limitation','P2',(5,5,4,3),'Route exhaustive counts through verified population/explicit-total logic and retain uncertainty when coverage is unknown.'),
('RET-06','Textual role labels can forge a user confirmation inside assistant content','confirmed_bug','P1',(5,5,5,3),'Validate quotes against structured original user-turn spans/IDs instead of reparsing role labels from free text.'),
('RET-07','English confirmation whitelist rejects supported Polish and present-tense acceptance','limitation','P2',(5,5,4,4),'Test language-aware assertion forms and provenance-linked confirmation, including Polish and present-tense acceptance; do not infer confirmation from keywords alone.'),
('RET-08','A matching quote is not proof of negation scope or same-fact resolution','limitation','P2',(5,5,4,3),'Add auxiliary entailment/state review using full source context and entity/fact links; preserve the existing semantic-verification disclaimer.'),
('RET-09','Update expansion gate lacks verified fact links and state completeness','limitation','P3',(4,4,3,3),'Evaluate fact-linked update coverage on labeled examples; do not interpret cue/term coverage as answerability.'),
('RET-10','Tiny-corpus BM25 negative IDF can reverse term-frequency preference','hypothesis','P3',(5,4,3,4),'Compare alternative IDF treatment or BM25 variants on frozen labels; retain exact-match baseline and measure ranking quality.'),
('RET-11','Investigation budget adjustment leaves stale excerpt trace metadata','confirmed_bug','P2',(5,5,4,5),'Recompute sent excerpt IDs/offsets/counts after pruning; distinguish excerpt count from grouped source count.'),
('RET-12','Decision-only snapshot mixes old evidence and new corpus revision','confirmed_bug','P2',(5,5,4,4),'Preserve the saved snapshot revision for decision-only work, or explicitly mark/reject changed-source provenance; do not silently relabel old evidence.'),
('RET-13','Service recovery depends on caller replay of failed prompt/date','limitation','P3',(4,3,2,4),'Make retry intent explicit or reconstruct failed operation inputs from the journal; the current UI already replays them.'),
('RET-14','Expansion budget can be consumed entirely by original candidates','limitation','P2',(5,5,3,3),'Experiment with a bounded quota for genuinely new expansion candidates while measuring the loss of corroborated high-rank precision.'),
('RET-15','Search timing includes query embedding timing','limitation','P3',(5,4,2,5),'Label timings inclusive/exclusive or subtract nested work; prevent misleading summation without claiming any observed latency improvement.'),
('RET-16','One retrieved chunk triggers unit work over its entire session','hypothesis','P2',(5,5,4,3),'Pre-index source spans/units and load only relevant ranges plus explicit context; benchmark real long-session latency and cache effects.'),
('RET-17','One retrieval mixes old ranked chunks with newly edited source text','confirmed_bug','P1',(5,5,5,4),'Bind candidate metadata, immutable content hashes and packing to one source snapshot; abort/retry explicitly if consistency cannot be established.'),
('RUN-01','Completed results lack immutable source-revision reuse/export guard','confirmed_bug','P1',(5,5,5,4),'Bind run/export to source snapshots and explicitly reject or label stale historical reuse; never auto-resend paid requests.'),
('RUN-02','Evaluation cache ignores material question/gold/source/build changes','confirmed_bug','P1',(5,5,5,4),'Use dataset/question/annotation/source/build/model provenance in report and frozen-selection identity.'),
('RUN-03','Citation labels can satisfy numeric answer gold','confirmed_bug','P1',(5,5,4,5),'Use canonical citation stripping before local answer matching and export, while preserving original responses for audit.'),
('RUN-04','Benchmark citation correction omits original evidence constraints','limitation','P2',(5,5,4,5),'Append repair instructions to the immutable constrained base question and reserve its full serialized budget.'),
('RUN-05','Store and transport disagree on inconsistent weekday dates','confirmed_bug','P3',(5,4,2,5),'Share a canonical date validator and reject invalid weekday/date pairs before persistence or remote changes.'),
('RUN-06','Installed package API is stale and crashes Build decision view','confirmed_bug','P1',(5,5,5,5),'Reinstall the intended release and restart via documented workflow; add normal-import installed-artifact UI smoke validation.'),
('RUN-07','Saved entry recovery state disappears with the browser session','confirmed_bug','P2',(5,5,4,4),'Persist entry/index/refresh job state and expose idempotent recovery after reconnect; identical same-date/content entry IDs already deduplicate.'),
('RUN-08','Citation-only answer becomes empty after export despite completed status','confirmed_bug','P2',(5,5,4,5),'Validate canonical answer content after citation stripping both before completion and during export.'),
('RUN-09','Comparisons confound cache state and convenience sampling','limitation','P2',(4,5,4,4),'Counterbalance matched runs; stratify history-disjoint samples and separately report cold/warm latency with cache state.'),
('RUN-10','Retrieval selection objective omits span/state and answer sufficiency','limitation','P2',(5,5,5,4),'Preserve official session metrics and add frozen auxiliary span/state labels plus held-out end-to-end evaluation before claiming an overall winner.'),
('RUN-11','Submission readiness is a count heuristic rather than exact release identity','limitation','P2',(5,5,4,4),'Validate a trusted dataset-release manifest and compatible completed preparation/frozen-selection stages, not just 146 IDs.'),
('RUN-12','Partial metrics and retry timing need explicit denominators and wall clock','limitation','P2',(4,5,4,4),'Report completed-conditional and whole-manifest metrics separately, with failure breakdowns and monotonic end-to-end elapsed time.'),
('RUN-13','Transport envelope and benchmark snapshot need stronger boundaries','hypothesis','P3',(3,4,3,4),'Subitem a: parent timeout/typed response with uncertain outcome and no blind retry. Subitem b: select compatible immutable benchmark snapshots by identity.'),
]
result=[]
for id,title,kind,sev,grades,fix in rows:
 group=id[:3]
 report={'ING':'ing-report.md','RET':'retrieval/report.md','RUN':'runtime/report.md'}[group]
 item=dict(id=id,title=title,classification=kind,severity=sev,evidence_grade=grades[0],fit_grade=grades[1],benefit_grade=grades[2],feasibility_grade=grades[3],disposition='merged' if id=='ING-15' else 'accepted',brief_fix=fix,group_report=report)
 if id=='ING-15': item['merged_into']='RET-09'
 if id=='RUN-13':
  item['subitems']=[{'id':'RUN-13a','title':'Subprocess deadline/envelope hardening','grades':[3,4,3,4]}, {'id':'RUN-13b','title':'Compatible benchmark snapshot selection','grades':[4,4,3,4]}]
 result.append(item)
(root/'findings.json').write_text(json.dumps(result,indent=2)+'\n')
counts={kind:sum(r['classification']==kind and r['disposition']=='accepted' for r in result) for kind in ('confirmed_bug','limitation','hypothesis')}
print(json.dumps({'registered':len(result),'accepted_distinct':sum(r['disposition']=='accepted' for r in result),'merged':1,'classifications':counts}))
