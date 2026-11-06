# Prism: LLM observability

Lightweight LLM observability, built as an independent side project to learn how tracing and evaluation work under the hood.

AI features are hard to debug: when an answer is wrong, it's not obvious which step failed, and a small prompt change can quietly make quality worse. Prism records every step, scores the answers and reports on both.

## Plan

- [x] Package scaffold and CI
- [x] Tracing: spans with timings, tokens, cost and nesting, stored in SQLite
- [x] Evaluators: relevance, faithfulness to sources, length checks
- [x] CLI report: latency percentiles, cost per step, error counts, regressions against a baseline

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

## Evaluating answers

```python
from prism.evals import Case, run_suite

sources = ["Refunds are issued to the original payment method within 5 days."]
result = run_suite([
    Case("When do refunds arrive?", "Refunds arrive within 5 days.", sources),
    Case("When do refunds arrive?", "Refunds arrive by drone tomorrow.", sources),
])
print(result.pass_rates)   # {'relevance': 1.0, 'faithfulness': 0.5, 'length': 1.0}
print(result.failures)     # the drone answer, flagged as unsupported by the sources
```

The checks are deterministic and need no API key: relevance measures how much of the question the answer covers, and faithfulness flags sentences whose content isn't backed by the retrieved sources. An LLM-as-judge evaluator is planned behind the same interface.

## CLI

```bash
pip install -e .
prism demo --requests 40              # simulate a small RAG app and record traces
prism report                          # summary per span
prism report --save-baseline base.json
prism report --baseline base.json     # exits 1 if latency, cost or errors got worse
```

```
span             count  errors  p50_ms  p95_ms  tokens  cost_usd
---------------  -----  ------  ------  ------  ------  --------
answer_question  40     0       9.63    13.7    0       0.0
generate         40     2       5.8     8.42    38546   0.008862
retrieve         40     0       2.83    4.83    0       0.0
```

The baseline check is designed for CI: record a run before a prompt or model change, then fail the build if things regress.

## Next

- LLM-as-judge evaluator behind the same interface
- Store eval scores alongside traces and show them in the report
- OpenTelemetry export
- A small web dashboard

## Develop

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Licence

MIT. A personal learning project, not client or employer work.
