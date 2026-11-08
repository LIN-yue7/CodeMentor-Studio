
import asyncio

from tools.evaluate_workbench import load_cases, run


def test_fixed_dataset_reports_abstentions_and_real_mode_separately():
    cases = load_cases()
    report = asyncio.run(run(cases, live=False))
    assert len(cases) >= 20
    assert report["summary"]["A"]["status"] == "not-run"
    assert report["summary"]["B"]["citations_present"] == 0
    assert report["summary"]["C"]["retrieval_expected_hit"] > 0
    assert report["summary"]["C"]["model_accepted"] == 0
    assert report["summary"]["C"]["clean_false_positive"] == 0
    assert any(row["variant"] == "C" and row["status"] == "uncertain" for row in report["rows"])
    assert report["exercise_review"]["templates"] == 9
