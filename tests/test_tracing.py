import pytest

from prism.store import TraceStore
from prism.tracing import Tracer, current_span


def test_spans_nest_into_one_trace():
    tracer = Tracer()
    with tracer.span("request") as root:
        with tracer.span("retrieve") as child:
            assert current_span() is child
        assert current_span() is root
    assert current_span() is None
    assert child.parent_id == root.span_id
    assert child.trace_id == root.trace_id
    assert root.duration_ms is not None and root.duration_ms >= 0


def test_decorator_creates_child_span():
    tracer = Tracer()

    @tracer.trace()
    def generate():
        return "ok"

    with tracer.span("request") as root:
        assert generate() == "ok"
    names = [s.name for s in tracer.finished]
    assert names == ["generate", "request"]
    assert tracer.finished[0].parent_id == root.span_id


def test_errors_are_recorded_and_reraised():
    tracer = Tracer()
    with pytest.raises(ValueError):
        with tracer.span("tool_call"):
            raise ValueError("bad input")
    assert tracer.finished[0].error == "ValueError: bad input"


def test_record_usage_prices_tokens():
    tracer = Tracer(prices={"m": (1.0, 2.0)})
    with tracer.span("generate") as span:
        cost = tracer.record_usage("m", input_tokens=500, output_tokens=1000)
    assert cost == pytest.approx(2.5)
    assert span.cost_usd == pytest.approx(2.5)
    assert (span.input_tokens, span.output_tokens, span.model) == (500, 1000, "m")


def test_record_usage_outside_span_fails():
    with pytest.raises(RuntimeError):
        Tracer().record_usage("m", 1, 1)


def test_store_round_trip():
    store = TraceStore()
    tracer = Tracer(store=store)
    with tracer.span("request", user="u1") as root:
        with tracer.span("generate"):
            tracer.record_usage("small-model", 100, 50)
    assert store.trace_ids() == [root.trace_id]
    spans = store.spans(root.trace_id)
    assert [s.name for s in spans] == ["request", "generate"]
    assert spans[0].attributes == {"user": "u1"}
    assert spans[1].output_tokens == 50
