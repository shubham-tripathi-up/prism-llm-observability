# Prism: LLM observability

Lightweight LLM observability, built as an independent side project to learn how tracing and evaluation work under the hood.

AI features are hard to debug: when an answer is wrong, it's not obvious which step failed, and a small prompt change can quietly make quality worse. Prism records every step, scores the answers and reports on both.

## Plan

- [x] Package scaffold and CI
- [ ] Tracing: spans with timings, tokens, cost and nesting, stored in SQLite
- [ ] Evaluators: relevance, faithfulness to sources, length checks
- [ ] CLI report: latency percentiles, cost per step, eval scores, regressions

No external dependencies; standard library only.

## Develop

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Licence

MIT. A personal learning project, not client or employer work.
