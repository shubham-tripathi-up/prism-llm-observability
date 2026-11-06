"""Command line: `prism demo` records sample traces, `prism report` summarises them."""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from typing import List, Optional

from .report import format_table, regressions, summarise
from .store import TraceStore
from .tracing import Tracer


def _demo(db: str, requests: int, seed: int) -> None:
    """Simulate a small RAG app so the report has something to show."""
    rng = random.Random(seed)
    tracer = Tracer(store=TraceStore(db))
    for _ in range(requests):
        with tracer.span("answer_question"):
            with tracer.span("retrieve"):
                time.sleep(rng.uniform(0.001, 0.004))
            try:
                with tracer.span("generate"):
                    time.sleep(rng.uniform(0.002, 0.008))
                    tracer.record_usage("small-model", rng.randint(400, 1200), rng.randint(60, 300))
                    if rng.random() < 0.05:
                        raise TimeoutError("model timed out")
            except TimeoutError:
                pass
    print(f"Recorded {requests} demo requests in {db}")


def _report(db: str, baseline: Optional[str], save_baseline: Optional[str]) -> int:
    summary = summarise(TraceStore(db).spans())
    if not summary:
        print("No spans recorded yet.")
        return 0
    print(format_table(summary))
    if save_baseline:
        with open(save_baseline, "w") as fh:
            json.dump(summary, fh, indent=2)
        print(f"\nSaved baseline to {save_baseline}")
    if baseline:
        with open(baseline) as fh:
            found = regressions(summary, json.load(fh))
        if found:
            print("\nRegressions:")
            for item in found:
                print(f"  - {item}")
            return 1
        print("\nNo regressions against the baseline.")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="prism", description="Lightweight LLM observability")
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="record sample traces from a simulated RAG app")
    demo.add_argument("--db", default="prism.db")
    demo.add_argument("--requests", type=int, default=50)
    demo.add_argument("--seed", type=int, default=7)

    report = sub.add_parser("report", help="summarise stored traces")
    report.add_argument("--db", default="prism.db")
    report.add_argument("--baseline", help="JSON summary to compare against; exits 1 on regressions")
    report.add_argument("--save-baseline", help="write the current summary as a baseline")

    args = parser.parse_args(argv)
    if args.command == "demo":
        _demo(args.db, args.requests, args.seed)
        return 0
    return _report(args.db, args.baseline, args.save_baseline)


if __name__ == "__main__":
    sys.exit(main())
