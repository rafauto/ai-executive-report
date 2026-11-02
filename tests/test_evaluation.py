from executive_report.cleaning import build_orders_view
from executive_report.data_loader import load_olist
from executive_report.evaluation import build_cases, pass_rate, run_eval, score_narrative
from executive_report.llm import NarrativeError, OfflineWriter
from helpers import GOOD_ANSWER, FakeWriter


def _cases(synthetic_dir):
    return build_cases(build_orders_view(load_olist(synthetic_dir)))


def test_offline_writer_passes_every_case(synthetic_dir):
    rows = run_eval(OfflineWriter(), _cases(synthetic_dir))
    assert len(rows) == 5
    assert pass_rate(rows) == 100.0


def test_scoring_catches_each_failure(synthetic_dir):
    case = next(c for c in _cases(synthetic_dir) if c.alerts)
    checks = score_narrative(GOOD_ANSWER + "\nNPS de 99,9%.", case.data, case.alerts)
    assert checks["has_all_sections"]
    assert not checks["no_unverified_numbers"]
    assert not checks["covers_every_alert"]
    assert not checks["three_to_five_recommendations"]
    assert not checks["reasonable_length"]


def test_failed_calls_count_as_failed_cases(synthetic_dir):
    rows = run_eval(FakeWriter(error=NarrativeError("down")), _cases(synthetic_dir))
    assert pass_rate(rows) == 0.0
    assert rows[0]["error"] == "NarrativeError: down"
