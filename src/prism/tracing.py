"""Tracing: record each step of an LLM app as a span.

A trace is a tree of spans. Each span has a name, timings, token usage, cost,
free-form attributes and an optional error. Spans nest automatically: a span
opened inside another becomes its child, including across function calls.
"""

from __future__ import annotations

import contextlib
import contextvars
import functools
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

# Price per 1K tokens (input, output) in USD. Override per Tracer as needed.
DEFAULT_PRICES: Dict[str, tuple] = {
    "small-model": (0.00015, 0.0006),
    "large-model": (0.0025, 0.01),
}


def _new_id(n: int = 16) -> str:
    return uuid.uuid4().hex[:n]


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str = field(default_factory=_new_id)
    parent_id: Optional[str] = None
    start: float = field(default_factory=time.time)
    end: Optional[float] = None
    model: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    attributes: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def duration_ms(self) -> Optional[float]:
        if self.end is None:
            return None
        return (self.end - self.start) * 1000

    def set(self, **attributes: Any) -> None:
        """Attach attributes, e.g. the prompt, retrieved doc ids or the answer."""
        self.attributes.update(attributes)


_current: contextvars.ContextVar[Optional[Span]] = contextvars.ContextVar(
    "prism_current_span", default=None
)


def current_span() -> Optional[Span]:
    """The span that is open in the current context, if any."""
    return _current.get()


class Tracer:
    """Creates spans and hands finished ones to an optional store."""

    def __init__(self, store: Any = None, prices: Optional[Dict[str, tuple]] = None):
        self.store = store
        self.prices = dict(DEFAULT_PRICES if prices is None else prices)
        self.finished: List[Span] = []

    @contextlib.contextmanager
    def span(self, name: str, **attributes: Any) -> Iterator[Span]:
        parent = _current.get()
        span = Span(
            name=name,
            trace_id=parent.trace_id if parent else _new_id(32),
            parent_id=parent.span_id if parent else None,
            attributes=dict(attributes),
        )
        token = _current.set(span)
        try:
            yield span
        except Exception as exc:
            span.error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            span.end = time.time()
            _current.reset(token)
            self.finished.append(span)
            if self.store is not None:
                self.store.save_span(span)

    def trace(self, name: Optional[str] = None) -> Callable[[F], F]:
        """Decorator form of :meth:`span`."""

        def decorator(fn: F) -> F:
            @functools.wraps(fn)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                with self.span(name or fn.__name__):
                    return fn(*args, **kwargs)

            return wrapper  # type: ignore[return-value]

        return decorator

    def record_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        span: Optional[Span] = None,
    ) -> float:
        """Record token usage on a span (the current one by default) and price it."""
        target = span or _current.get()
        if target is None:
            raise RuntimeError("record_usage called outside a span")
        in_price, out_price = self.prices.get(model, (0.0, 0.0))
        cost = input_tokens / 1000 * in_price + output_tokens / 1000 * out_price
        target.model = model
        target.input_tokens += input_tokens
        target.output_tokens += output_tokens
        target.cost_usd += cost
        return cost
