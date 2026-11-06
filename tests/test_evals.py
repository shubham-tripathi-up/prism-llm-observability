from prism.evals import Case, faithfulness, length, relevance, run_suite

SOURCES = ["Orders ship within 2 business days. Refunds are issued to the original payment method within 5 days."]


def test_relevance_scores_question_coverage():
    good = relevance("When do refunds arrive?", "Refunds arrive within 5 days.")
    bad = relevance("When do refunds arrive?", "Our store sells shoes.")
    assert good.passed and good.score == 1.0
    assert not bad.passed and "refunds" in bad.details["missing"]


def test_faithfulness_flags_unsupported_sentences():
    answer = "Refunds are issued within 5 days. You also get a free gift voucher."
    result = faithfulness(answer, SOURCES)
    assert result.score == 0.5
    assert not result.passed
    assert result.details["unsupported"] == ["You also get a free gift voucher."]


def test_faithfulness_passes_grounded_answer():
    assert faithfulness("Orders ship within 2 business days.", SOURCES).passed


def test_faithfulness_without_sources_fails():
    assert not faithfulness("Anything at all.", []).passed


def test_length_bounds():
    assert length("one two three").passed
    assert not length("hi").passed
    assert length("word " * 300).details["words"] == 300


def test_run_suite_summarises():
    cases = [
        Case("How long does shipping take?", "Orders ship within 2 business days.", SOURCES),
        Case("When do refunds arrive?", "Refunds arrive by drone tomorrow.", SOURCES),
    ]
    result = run_suite(cases)
    assert result.pass_rates["faithfulness"] == 0.5
    assert any(f["case"] == 1 and f["eval"] == "faithfulness" for f in result.failures)
    assert 0 < result.averages["relevance"] <= 1
