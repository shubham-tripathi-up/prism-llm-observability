# Prism: LLM observability

Lightweight LLM observability, built as an independent side project to learn how tracing and evaluation work under the hood.

AI features are hard to debug: when an answer is wrong, it's not obvious which step failed, and a small prompt change can quietly make quality worse. Prism records every step, scores the answers and reports on both.

## Plan

- [x] Package scaffold and CI
- [x] Tracing: spans with timings, tokens, cost and nesting, stored in SQLite
- [ ] Evaluators: relevance, faithfulness to sources, length checks
- [ ] CLI report: latency percentiles, cost per step, eval scores, regressions

No external dependencies; standard library only.

## Tracing

```python
from prism.store import TraceStore
from prism.tracing import Tracer

tracer = Tracer(store=TraceStore("traces.db"))

@tracer.trace()
def retrieve(question):
    return ["doc-1", "doc-2"]

with tracer.span("answer_question", question="Where is my order?") as span:
    docs = retrieve(span.attributes["question"])
    with tracer.span("generate"):
        tracer.record_usage("small-model", input_tokens=820, output_tokens=140)
```

Spans opened inside other spans become their children, errors are recorded and re-raised, and token usage is priced per model.

## Develop

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Licence

MIT. A personal learning project, not client or employer work.
