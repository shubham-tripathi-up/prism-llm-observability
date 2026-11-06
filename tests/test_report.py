import json

from prism.cli import main
from prism.report import percentile, regressions, summarise
from prism.tracing import Span


def make(name, ms, cost=0.0, error=None):
    return Span(name=name, trace_id="t", start=0.0, end=ms / 1000, cost_usd=cost, error=error)


def test_percentile_nearest_rank():
    assert percentile([], 95) == 0.0
    assert percentile([5, 1, 3], 50) == 3
    assert percentile(list(range(1, 101)), 95) == 95


def test_summarise_groups_by_name():
    summary = summarise([make("gen", 100, 0.01), make("gen", 300, 0.03, "Timeout"), make("ret", 10)])
    assert summary["gen"]["count"] == 2
    assert summary["gen"]["errors"] == 1
    assert summary["gen"]["p95_ms"] == 300
    assert summary["gen"]["cost_usd"] == 0.04
    assert summary["ret"]["count"] == 1


def test_regressions_flag_latency_cost_and_errors():
    base = {"gen": {"count": 10, "errors": 0, "p95_ms": 100, "cost_usd": 0.10}}
    now = {"gen": {"count": 10, "errors": 2, "p95_ms": 150, "cost_usd": 0.20}}
    found = regressions(now, base)
    assert len(found) == 3
    assert regressions(base, base) == []


def test_cli_demo_report_and_baseline(tmp_path, capsys):
    db = str(tmp_path / "p.db")
    baseline = str(tmp_path / "base.json")
    assert main(["demo", "--db", db, "--requests", "10"]) == 0
    assert main(["report", "--db", db, "--save-baseline", baseline]) == 0
    out = capsys.readouterr().out
    assert "answer_question" in out and "generate" in out
    assert json.load(open(baseline))["retrieve"]["count"] == 10
    assert main(["report", "--db", db, "--baseline", baseline]) == 0
