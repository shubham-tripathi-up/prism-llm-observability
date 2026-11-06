"""SQLite storage for spans and evaluation scores."""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional

from .tracing import Span

_SCHEMA = """
CREATE TABLE IF NOT EXISTS spans (
    span_id       TEXT PRIMARY KEY,
    trace_id      TEXT NOT NULL,
    parent_id     TEXT,
    name          TEXT NOT NULL,
    start         REAL NOT NULL,
    end           REAL,
    model         TEXT,
    input_tokens  INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd      REAL NOT NULL DEFAULT 0,
    attributes    TEXT NOT NULL DEFAULT '{}',
    error         TEXT
);
CREATE INDEX IF NOT EXISTS idx_spans_trace ON spans (trace_id);
CREATE INDEX IF NOT EXISTS idx_spans_name ON spans (name);
"""


class TraceStore:
    def __init__(self, path: str = ":memory:"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)

    def save_span(self, span: Span) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO spans VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                span.span_id,
                span.trace_id,
                span.parent_id,
                span.name,
                span.start,
                span.end,
                span.model,
                span.input_tokens,
                span.output_tokens,
                span.cost_usd,
                json.dumps(span.attributes, default=str),
                span.error,
            ),
        )
        self.conn.commit()

    def spans(self, trace_id: Optional[str] = None) -> List[Span]:
        sql = "SELECT * FROM spans"
        params: tuple = ()
        if trace_id is not None:
            sql += " WHERE trace_id = ?"
            params = (trace_id,)
        rows = self.conn.execute(sql + " ORDER BY start", params).fetchall()
        return [self._to_span(r) for r in rows]

    def trace_ids(self) -> List[str]:
        rows = self.conn.execute(
            "SELECT trace_id, MIN(start) AS s FROM spans GROUP BY trace_id ORDER BY s"
        ).fetchall()
        return [r["trace_id"] for r in rows]

    def close(self) -> None:
        self.conn.close()

    @staticmethod
    def _to_span(row: sqlite3.Row) -> Span:
        data: Dict[str, Any] = dict(row)
        data["attributes"] = json.loads(data["attributes"])
        return Span(**data)
