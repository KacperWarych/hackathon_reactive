# Retrieval models for Sales Blocker Memory

Research date: 2026-10-30. Status: architecture recommendation; no candidate models have been benchmarked or installed in this task.

## Recommendation

Start with **BM25 + Qwen/Qwen3-Embedding-0.6B + reciprocal rank fusion (RRF) + Qwen/Qwen3-Reranker-0.6B**. Use a conditional second retrieval pass for missing updates or evidence, then give a bounded selection of original excerpts to Reactor for the final answer. The long-conversation implementation added on 2026-10-31 defaults to 2,000 evidence-text tokens and six excerpts; the model shortlist below remains an unbenchmarked architecture recommendation.

Compare this against **BAAI/bge-m3 dense + sparse retrieval + BAAI/bge-reranker-v2-m3**. If short replies lose their meaning when chunked, evaluate **perplexity-ai/pplx-embed-context-v1-0.6b** for contextual passage embeddings, paired with its standard query embedding model, while retaining BM25 and a reranker.

This preference reflects task fit and implementation scope, not a measured ranking on this dataset. Runtime and throughput must be measured on the team's hardware.

## Inputs inspected

- [Sales Blocker Memory brief](/Users/kacperwarych/Documents/Codex/2026-10-30/files-mentioned-by-the-user-screenshot/outputs/sales-blocker-memory-use-case.md), from the chat “Review hackathon slides and use”.
- [Development archive](/Users/kacperwarych/Downloads/dev.tar.gz): 470 histories, 526 questions, 22,428 sessions.
- [Large development archive](/Users/kacperwarych/Downloads/dev-large.tar.gz): 470 histories, 526 questions, 222,321 sessions.
- [Test archive](/Users/kacperwarych/Downloads/test.tar.gz): 15 histories, 146 questions, exactly 200 sessions per history.
- [Challenge format guide](/Users/kacperwarych/Downloads/memory-challenge-main/format.md) and [participant guide](/Users/kacperwarych/Downloads/memory-challenge-main/reactor/QUICKSTART.md).

Development gold contains 70 single-session-user, 112 single-session-assistant, 133 multi-session, 133 temporal-reasoning, and 78 knowledge-update questions. Thirty questions require abstention. The supplied conversations include consumer purchases and personal decisions, but the inspected records do not establish a real B2B sales pipeline or labeled sales blockers.

Actual development questions include “What type of camera lens did I purchase most recently?”, “Where am I planning to stay for my birthday trip to Hawaii?”, and “How many magazine subscriptions do I currently have?”. Their gold evidence spans multiple sessions. These demonstrate retrieval requirements shared with the proposed product: recover updates, distinguish intentions from actions, and collect several pieces of evidence.

## Shortlist

| Option | Models and retrieval | Fit | Tradeoff |
| --- | --- | --- | --- |
| First implementation | BM25; Qwen3-Embedding-0.6B; Qwen3-Reranker-0.6B | Exact products and names plus paraphrased concerns; instruction-aware ranking | Two neural stages; indexing and reranking speed need measurement |
| Main comparison | BGE-M3 dense and sparse; bge-reranker-v2-m3 | One encoder supplies two retrieval signals; multilingual sales extension | Must use an inference path exposing sparse output; ordinary dense-only encoding is not hybrid search |
| Context experiment | BM25; pplx-embed-context-v1-0.6b passages; pplx-embed-v1-0.6b queries; Qwen3 reranker | Short replies and references whose meaning depends on surrounding turns | More indexing complexity; context must be bounded by session/thread and question time |
| Resource-constrained baseline | BM25; BAAI/bge-small-en-v1.5; cross-encoder/ms-marco-MiniLM-L6-v2 | English data, smaller models, fast iteration candidate | Short input limits; less suitable as a multilingual product default; compare quality empirically |

Qwen's model cards document 0.6B, 4B, and 8B variants for embedding and reranking. The 0.6B embedding produces up to 1,024 dimensions and accepts up to 32K tokens; both model types support instructions. Use the published task-specific input formatting, pooling, and normalization. Start with the smaller pair; test a 4B upgrade only after identifying retrieval or reranking failures that justify the extra compute. A long input limit does not imply that embedding an entire noisy history is a good retrieval unit. Sources: [Qwen embedding](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B), [Qwen reranker](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B).

BGE-M3 supports dense, learned sparse, and multi-vector retrieval, over 100 languages, and up to 8,192 tokens. Start with dense+sparse; add multi-vector scoring only as an evaluated experiment. Its sparse weights are a learned lexical signal, not BM25 scores. Keep a BM25 baseline to measure whether exact-name and product-code retrieval improves. Sources: [BGE-M3](https://huggingface.co/BAAI/bge-m3), [BGE reranker](https://huggingface.co/BAAI/bge-reranker-v2-m3).

Perplexity's contextual model embeds passages using surrounding document context. Its standard sibling handles independent queries. The 0.6B versions provide 1,024-dimensional embeddings and a 32K context limit. Follow the paired model's documented encoding and cosine-similarity requirements; do not combine Qwen query vectors with Perplexity passage vectors. Contextual embeddings help represent a reply but do not prove that two separate sessions describe the same deal. Sources: [contextual model](https://huggingface.co/perplexity-ai/pplx-embed-context-v1-0.6b), [standard model](https://huggingface.co/perplexity-ai/pplx-embed-v1-0.6b).

For the smaller English baseline, BGE-small-en-v1.5 provides 384-dimensional embeddings with a 512-token input limit; leave room for required input formatting. MiniLM-L6-v2 is a passage-ranking cross-encoder trained on MS MARCO. Measure speed locally rather than copying published throughput from different hardware. Sources: [BGE-small](https://huggingface.co/BAAI/bge-small-en-v1.5), [MiniLM reranker](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2).

## Proposed hybrid pipeline

All numeric settings below are starting values for development experiments.

1. **Scope by history and time.** Apply the exact `history_id` filter before retrieving. Parse session and question dates, retaining original date strings. In a future sales dataset also scope by buyer/deal when those identifiers are present. Never invent a deal identity from topical similarity.
2. **Create contextual excerpts.** Begin with about 350–600 tokens, respecting message boundaries and preserving role labels. Keep the initiating question and neighboring reply when useful; split very long messages with overlap. Store session ID, turn IDs/order, date, and original text. Use shorter chunks for the 512-token baseline. Do not silently truncate full sessions.
3. **Retrieve through two channels.** For the first stack retrieve the top 40 BM25 and top 40 dense chunks within the permitted history. BM25 helps with exact names, model numbers, amounts, and specific terms; dense retrieval finds paraphrases such as “cannot commit annually” versus “contract-term constraint.” These are expected complementary strengths, not guarantees.
4. **Fuse ranks.** Use RRF with rank constant 60 as an initial setting. It combines rank positions rather than adding incomparable raw BM25 and cosine scores. Deduplicate overlapping chunks. Source: [RRF documentation](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion).
5. **Rerank the top 40–60 candidates.** Score the exact question against each excerpt including relevant contextual turns. Treat scores as relevance signals, not probabilities that an answer is correct. Preserve coverage of separate subquestions; a single passage's high rank does not establish a complete multi-session answer.
6. **Search again only when evidence appears incomplete.** Extract grounded names/products/events and search for updates, resolutions, reversals, and missing parts. For “current” questions search later sessions up to the question date. For historical questions search the relevant interval. Keep the original query branch so a mistaken expansion cannot eliminate good evidence.
7. **Construct an evidence bundle.** Merge useful excerpts from the same session, keep chronological context, and map citations to session IDs. Reserve space for the question, dates, labels, and any instructions inside the client's 16,000-character default limit. The implemented starting limits are 2,000 evidence-text tokens, 8,000 evidence characters, six excerpts, and 320 tokens per excerpt. Token counts use the embedding tokenizer; measure the complete serialized request separately.
8. **Have Reactor assess and answer.** Provide original evidence, any clearly marked extracted candidates, and computed date differences/totals where appropriate. Reactor must produce the final challenge answer. Maintain one Reactor history per dataset history and reuse it across that history's questions, following the kit.

For the product question “What still blocks the purchase?”, use separate searches for requirements/concerns, later changes or resolutions, approval/commitment status, and missing information. For official benchmark questions, use question-specific expansion; do not add sales terminology to every query.

The original LongMemEval research supports testing decomposed sessions, fact-augmented retrieval keys, and time-aware query expansion. This is directly relevant to the development data, although the organizers' new test distribution still needs empirical validation. Source: [LongMemEval paper](https://arxiv.org/abs/2410.10813).

## State tracking for the sales use case

Maintain an evidence-linked event ledger alongside retrieval:

`entity/deal reference | concern or fact | speaker | assertion type | session date | stated event date | status candidate | source session/turn`

Assertion types can distinguish a buyer statement, assistant recommendation, hypothetical option, commitment, completed action, or explicit resolution. Missing event dates and unresolved entity links stay unknown. Candidate statuses might be raised, explicitly resolved, superseded, or uncertain. Status assignment requires examining the evidence; the schema itself does not determine truth.

For the brief's fictional integration example, retrieve the initial concern and search for the subsequent clearance. Also search for remaining procurement approval and possible pilot terms. The seller offering an integration workaround does not establish buyer acceptance. A later hypothetical does not automatically override a confirmed earlier statement. A global recency boost would be insufficient.

Use the ledger as an additional retrieval path and a traceable view, retaining original text. Begin with ordinary structured records; a full graph retrieval platform is not required to demonstrate this behavior. Across-deal analysis would need genuine distinct deal identifiers and coverage beyond top-k search before counting recurring blockers.

## Evaluation and selection

1. Split development by `history_id`, keeping alternative questions about the same history together. Keep the corresponding dev and dev-large versions in the same partition. They are the same questions at different noise levels, not independent evaluation sets. If fine-tuning later, audit shared evidence/session content across partitions too.
2. Compare BM25 alone, dense alone, BM25+dense RRF, hybrid+reranker, and hybrid+reranker+update searches. Use the same chunks and evidence budget to isolate model changes.
3. Compare the Qwen and BGE stacks. Hold the reranker fixed for a retriever-only comparison, then swap rerankers separately. Add the contextual experiment only if errors show lost references or incomplete chunk context.
4. Measure gold-session recall at fixed candidate counts, the percentage of questions with all required evidence recovered, and evidence retained after context packing. Measure official session evidence F1, answer accuracy, abstention behavior, indexing time, query latency, and memory use. Report by question type.
5. The supplied scoring script can leave answers unjudged; do not interpret its automatic matches as the complete official LLM-judged accuracy.
6. Calibrate abstention on held-out development examples. Neither cosine similarity, RRF, nor a sigmoid reranker score is a calibrated answerability probability. Only 30 dev questions are unanswerable, so report that limited sample size.
7. For the sales product, separately review supported purchasing/decision histories for current-versus-resolved concerns, hypothetical-versus-confirmed actions, and incorrect entity links. The official gold does not label sales blocker states.

Avoid fine-tuning or indexing the entire large split as the first step. Establish a reproducible retrieval baseline, then use held-out dev-large histories to test noise sensitivity. Cache content embeddings where session text repeats; if the representation includes a date or history-specific context, include those in the cache key because a session's date can differ between histories.

## Practical choice

Build the Qwen hybrid first, compare BGE-M3 under the same evaluation, and prioritize reliable update retrieval and source coverage before increasing model size. Run all retrieval models locally for the initial challenge implementation, consistent with the documented allowance for local models. The final answer remains Reactor's responsibility.
