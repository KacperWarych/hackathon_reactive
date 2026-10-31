# Decision memory — final-session speaking outline

Adapt timing and slide format to the kickoff announcement.

1. **Problem.** Answer questions across long, noisy conversation histories,
   including near misses, changed facts, dates, and genuinely missing answers.
2. **Retrieval.** Combine BM25 and pinned Qwen embeddings with reciprocal rank
   fusion, rerank candidates, then make one bounded update-search pass. Pack
   original speaker-labelled excerpts into a small context with session IDs and
   dates. Tune retrieval on development data; keep held-out validation separate.
3. **Answering.** Reactor produces final answers. Use the latest eligible mention
   for updates to the same fact and session dates for temporal questions.
   Insufficient evidence leads to abstention. Validate citations against supplied
   sessions; transport failures remain incomplete, never fabricated abstentions.
4. **Demo and evidence.** Show one real development question, retrieved excerpts,
   and its saved Reactor answer; then show an update and an abstention if completed
   runs are available. Report only measured results from the actual evaluation
   reports. Offline tests alone do not establish live answer accuracy or latency.
5. **Delivery and limits.** Submit predictions.jsonl and the runnable code archive.
   Explain resumable request records and citation checks. Bounded retrieval can
   miss evidence; retrieval scores are not confidence probabilities. Population
   totals require a recorded total or complete coverage.

Before presenting: insert measured validation results and prepare the actual
saved examples. No performance numbers or live outcomes are claimed by this outline.
