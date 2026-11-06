"""Answer evaluators.

Cheap, deterministic checks that run without calling a model:

- relevance:     how much of the question the answer actually addresses
- faithfulness:  how much of the answer is supported by the retrieved sources;
                 unsupported sentences are flagged as likely hallucinations
- length:        whether the answer is within a sensible word range

An LLM-as-judge evaluator can be added later behind the same interface.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from statistics import mean
from typing import Dict, List, Sequence

_WORD = re.compile(r"[a-z0-9]+")
_SENTENCE = re.compile(r"(?<=[.!?])\s+")
STOPWORDS = frozenset(
    """a an and are as at be but by can do does for from has have how i if in is it
    its me my of on or our so that the their them then there these this to was we
    were what when where which who why will with you your""".split()
)


def content_words(text: str) -> set:
    return {w for w in _WORD.findall(text.lower()) if w not in STOPWORDS}


def sentences(text: str) -> List[str]:
    return [s.strip() for s in _SENTENCE.split(text.strip()) if s.strip()]


@dataclass
class EvalResult:
    name: str
    score: float
    passed: bool
    details: Dict[str, object] = field(default_factory=dict)


def relevance(question: str, answer: str, threshold: float = 0.5) -> EvalResult:
    q = content_words(question)
    if not q:
        return EvalResult("relevance", 1.0, True)
    covered = q & content_words(answer)
    score = len(covered) / len(q)
    return EvalResult(
        "relevance", score, score >= threshold, {"missing": sorted(q - covered)}
    )


def faithfulness(
    answer: str,
    sources: Sequence[str],
    sentence_threshold: float = 0.6,
    threshold: float = 0.8,
) -> EvalResult:
    """Share of answer sentences whose content words mostly appear in the sources."""
    source_words = set().union(*(content_words(s) for s in sources)) if sources else set()
    parts = sentences(answer)
    if not parts:
        return EvalResult("faithfulness", 0.0, False, {"unsupported": []})
    unsupported = []
    for sentence in parts:
        words = content_words(sentence)
        support = len(words & source_words) / len(words) if words else 1.0
        if support < sentence_threshold:
            unsupported.append(sentence)
    score = 1 - len(unsupported) / len(parts)
    return EvalResult(
        "faithfulness", score, score >= threshold, {"unsupported": unsupported}
    )


def length(answer: str, min_words: int = 3, max_words: int = 200) -> EvalResult:
    n = len(answer.split())
    ok = min_words <= n <= max_words
    return EvalResult("length", 1.0 if ok else 0.0, ok, {"words": n})


@dataclass
class Case:
    question: str
    answer: str
    sources: List[str] = field(default_factory=list)


def evaluate(case: Case) -> List[EvalResult]:
    return [
        relevance(case.question, case.answer),
        faithfulness(case.answer, case.sources),
        length(case.answer),
    ]


@dataclass
class SuiteResult:
    averages: Dict[str, float]
    pass_rates: Dict[str, float]
    failures: List[Dict[str, object]]


def run_suite(cases: Sequence[Case]) -> SuiteResult:
    """Evaluate a test set and summarise scores, pass rates and failing cases."""
    by_name: Dict[str, List[EvalResult]] = {}
    failures = []
    for i, case in enumerate(cases):
        for result in evaluate(case):
            by_name.setdefault(result.name, []).append(result)
            if not result.passed:
                failures.append(
                    {"case": i, "eval": result.name, "score": round(result.score, 3),
                     "details": result.details}
                )
    return SuiteResult(
        averages={k: mean(r.score for r in v) for k, v in by_name.items()},
        pass_rates={k: sum(r.passed for r in v) / len(v) for k, v in by_name.items()},
        failures=failures,
    )
