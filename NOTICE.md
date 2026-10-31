# Sources and third-party components

- `src/decision_memory/vendor/reactor_client.py` is copied from the supplied `memory-challenge-main/reactor/client.py` participant kit.
- `src/decision_memory/vendor/score.py` is copied from the supplied challenge scoring script. Consult the organizers' distribution terms before redistributing their kit.
- Qwen model weights and input formatting: [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B), [Qwen3-Reranker-0.6B](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B), Apache 2.0 as declared by their publishers. Model files remain in the ignored local cache.
- [LongMemEval research](https://arxiv.org/abs/2410.10813) motivates session decomposition and time-aware retrieval. The official hackathon release includes adapted development data and a separately constructed test split.

No dataset, credentials, model weights, or live Reactor answers are bundled with the source code.
