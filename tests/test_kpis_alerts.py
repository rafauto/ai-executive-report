import pandas as pd
import pytest

from executive_report.alerts import SEVERITY_ORDER, evaluate_alerts
from executive_report.cleaning import build_orders_view
from executive_report.config import AlertThresholds
from executive_report.kpis import build_report_data, period_kpis

AUG = pd.Period("2018-08", "M")


@pytest.fixture
def view(tiny_tables):
    return build_orders_view(tiny_tables)


def test_period_kpis_known_values(view):
    k = period_kpis(view, AUG)
    assert k["revenue"] == pytest.approx(60 + 90 + 80)  # canceled order excluded
    assert k["orders"] == 3
    assert k["avg_ticket"] == pytest.approx(230 / 3, rel=1e-3)
    assert k["unique_customers"] == 2  # u3 bought twice
    assert k["cancel_rate_pct"] == pytest.approx(25.0)
    assert k["late_delivery_pct"] == pytest.approx(33.33, abs=0.01)
    assert k["avg_review_score"] == pytest.approx(3.0)
    assert k["negative_review_pct"] == pytest.approx(33.33, abs=0.01)


def test_month_over_month_change(view):
    data = build_report_data(view, AUG, min_state_orders=1)
    assert data["previous_month"] == "2018-07"
    assert data["mom_change_pct"]["revenue"] == pytest.approx(100 * (230 - 330) / 330, abs=0.01)


def test_month_without_previous_data_has_null_change(view):
    data = build_report_data(view, pd.Period("2018-07", "M"))
    assert data["mom_change_pct"]["revenue"] is None


def test_alerts_fire_and_are_sorted_by_severity(view):
    data = build_report_data(view, AUG, min_state_orders=1)
    alerts = evaluate_alerts(data)
    codes = [a.code for a in alerts]
    for expected in ["REVENUE_DROP", "LATE_DELIVERIES", "HIGH_CANCELLATIONS", "LOW_REVIEW_SCORE"]:
        assert expected in codes
    ranks = [SEVERITY_ORDER[a.severity] for a in alerts]
    assert ranks == sorted(ranks)


def test_no_alerts_when_thresholds_are_loose(view):
    data = build_report_data(view, AUG, min_state_orders=1)
    loose = AlertThresholds(
        revenue_drop_pct=-99,
        orders_drop_pct=-99,
        late_delivery_pct=99,
        cancel_rate_pct=99,
        min_review_score=0,
        negative_review_pct=99,
        category_drop_pct=-100,
        state_late_pct=101,
    )
    assert evaluate_alerts(data, loose) == []


def test_alert_text_uses_brazilian_number_format(view):
    data = build_report_data(view, AUG, min_state_orders=1)
    detail = next(a for a in evaluate_alerts(data) if a.code == "REVENUE_DROP").detail
    assert "30,3%" in detail
