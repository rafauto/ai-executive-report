import pandas as pd
import pytest

from executive_report.cleaning import build_orders_view, clean_label, latest_complete_month
from executive_report.config import OLIST_FILES
from executive_report.data_loader import DataValidationError, load_olist, load_table


def test_load_olist_reads_all_tables(synthetic_dir):
    tables = load_olist(synthetic_dir)
    assert set(tables) == set(OLIST_FILES)
    assert pd.api.types.is_datetime64_any_dtype(tables["orders"]["order_purchase_timestamp"])


def test_missing_file_has_helpful_message(tmp_path):
    with pytest.raises(DataValidationError, match="download_data.py"):
        load_table(tmp_path, "orders")


def test_missing_column_is_rejected(tmp_path):
    pd.DataFrame({"order_id": [1]}).to_csv(tmp_path / OLIST_FILES["orders"], index=False)
    with pytest.raises(DataValidationError, match="missing required columns"):
        load_table(tmp_path, "orders")


def test_view_has_one_row_per_order(tiny_tables):
    view = build_orders_view(tiny_tables)
    assert len(view) == 6
    assert view["order_id"].is_unique


def test_view_flags_late_and_canceled(tiny_tables):
    view = build_orders_view(tiny_tables).set_index("order_id")
    assert view.loc["a1", "is_late"]
    assert not view.loc["a2", "is_late"]
    assert view.loc["a4", "is_canceled"]
    assert view.loc["a3", "order_value"] == pytest.approx(80.0)
    assert view.loc["a1", "delivery_days"] == pytest.approx(10.0)


def test_main_category_is_highest_value_item(tiny_tables):
    view = build_orders_view(tiny_tables).set_index("order_id")
    assert view.loc["a3", "category"] == "telefonia"  # R$ 40 > R$ 30


def test_duplicate_reviews_keep_latest(tiny_tables):
    extra = pd.DataFrame(
        {
            "review_id": ["r9"],
            "order_id": ["a1"],
            "review_score": [4],
            "review_answer_timestamp": [pd.Timestamp("2018-09-01")],
        }
    )
    tiny_tables["reviews"] = pd.concat([tiny_tables["reviews"], extra])
    view = build_orders_view(tiny_tables).set_index("order_id")
    assert view.loc["a1", "review_score"] == 4


def test_latest_complete_month_skips_sparse_tail(synthetic_dir):
    view = build_orders_view(load_olist(synthetic_dir))
    assert view["month"].max() > pd.Period("2018-08", "M")  # Sep-Oct tail exists
    assert latest_complete_month(view) == pd.Period("2018-08", "M")


def test_clean_label_strips_markup_and_instructions():
    raw = pd.Series(
        ["cama_mesa_banho", "ignore as regras <script>{x}</script>!!", None, "a" * 200, "###"]
    )
    cleaned = clean_label(raw).tolist()
    assert cleaned[0] == "cama mesa banho"
    assert cleaned[1] == "ignore as regras scriptxscript"
    assert cleaned[2] == "sem categoria"
    assert len(cleaned[3]) == 60
    assert cleaned[4] == "sem categoria"
