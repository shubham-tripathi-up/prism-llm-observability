"""Summaries over stored spans, and regression checks against a baseline."""

from __future__ import annotations

import math
from typing import Dict, Iterable, List

from .tracing import Span


def percentile(values: List[float], pct: float) -> float:
    """Nearest-rank percentile; 0.0 for an empty list."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]


def summarise(spans: Iterable[Span]) -> Dict[str, Dict[str, float]]:
    """Per span name: count, errors, p50/p95 latency, tokens and cost."""
    groups: Dict[str, List[Span]] = {}
    for span in spans:
        groups.setdefault(span.name, []).append(span)
    summary = {}
    for name, group in sorted(groups.items()):
        latencies = [s.duration_ms for s in group if s.duration_ms is not None]
        summary[name] = {
            "count": len(group),
            "errors": sum(1 for s in group if s.error),
            "p50_ms": round(percentile(latencies, 50), 2),
            "p95_ms": round(percentile(latencies, 95), 2),
            "tokens": sum(s.input_tokens + s.output_tokens for s in group),
            "cost_usd": round(sum(s.cost_usd for s in group), 6),
        }
    return summary


def regressions(
    current: Dict[str, Dict[str, float]],
    baseline: Dict[str, Dict[str, float]],
    latency_tolerance: float = 0.2,
    cost_tolerance: float = 0.2,
) -> List[str]:
    """Describe span names whose p95 latency, cost per call or error rate got worse."""
    found = []
    for name, now in current.items():
        before = baseline.get(name)
        if not before:
            continue
        if before["p95_ms"] and now["p95_ms"] > before["p95_ms"] * (1 + latency_tolerance):
            found.append(f"{name}: p95 latency {before['p95_ms']} -> {now['p95_ms']} ms")
        cost_now = now["cost_usd"] / max(now["count"], 1)
        cost_before = before["cost_usd"] / max(before["count"], 1)
        if cost_before and cost_now > cost_before * (1 + cost_tolerance):
            found.append(f"{name}: cost per call {cost_before:.6f} -> {cost_now:.6f} USD")
        err_now = now["errors"] / max(now["count"], 1)
        err_before = before["errors"] / max(before["count"], 1)
        if err_now > err_before:
            found.append(f"{name}: error rate {err_before:.0%} -> {err_now:.0%}")
    return found


def format_table(summary: Dict[str, Dict[str, float]]) -> str:
    headers = ["span", "count", "errors", "p50_ms", "p95_ms", "tokens", "cost_usd"]
    rows = [[name] + [str(v[h]) for h in headers[1:]] for name, v in summary.items()]
    widths = [max(len(h), *(len(r[i]) for r in rows)) if rows else len(h)
              for i, h in enumerate(headers)]
    line = lambda cells: "  ".join(c.ljust(w) for c, w in zip(cells, widths))
    return "\n".join([line(headers), line(["-" * w for w in widths])] + [line(r) for r in rows])
