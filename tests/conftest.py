from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from executive_report.config import OLIST_FILES  # noqa: E402


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "gen", ROOT / "scripts" / "generate_sample_data.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def synthetic_dir(tmp_path_factory) -> Path:
    """Small synthetic sample written to disk in the Kaggle layout."""
    out = tmp_path_factory.mktemp("olist")
    for name, df in _load_generator().generate(n_orders=3000, seed=7).items():
        df.to_csv(out / OLIST_FILES[name], index=False)
    return out


@pytest.fixture
def tiny_tables() -> dict[str, pd.DataFrame]:
    """Minimal dataset with hand-checked results.

    July/2018: 2 orders delivered on time (R$ 110 and R$ 220).
    August/2018: 3 valid orders (1 late) + 1 canceled.
    """
    ts = pd.Timestamp
    orders = pd.DataFrame(
        {
            "order_id": ["j1", "j2", "a1", "a2", "a3", "a4"],
            "customer_id": ["c1", "c2", "c3", "c4", "c5", "c6"],
            "order_status": [
                "delivered",
                "delivered",
                "delivered",
                "delivered",
                "delivered",
                "canceled",
            ],
            "order_purchase_timestamp": [
                ts("2018-07-05"),
                ts("2018-07-10"),
                ts("2018-08-01"),
                ts("2018-08-02"),
                ts("2018-08-03"),
                ts("2018-08-04"),
            ],
            "order_approved_at": pd.NaT,
            "order_delivered_carrier_date": pd.NaT,
            "order_delivered_customer_date": [
                ts("2018-07-10"),
                ts("2018-07-15"),
                ts("2018-08-11"),
                ts("2018-08-06"),
                ts("2018-08-08"),
                pd.NaT,
            ],
            "order_estimated_delivery_date": [
                ts("2018-07-20"),
                ts("2018-07-25"),
                ts("2018-08-05"),
                ts("2018-08-20"),
                ts("2018-08-20"),
                ts("2018-08-20"),
            ],
        }
    )
    items = pd.DataFrame(
        {
            "order_id": ["j1", "j2", "a1", "a2", "a3", "a3", "a4"],
            "order_item_id": [1, 1, 1, 1, 1, 2, 1],
            "product_id": ["p1", "p2", "p1", "p2", "p1", "p2", "p1"],
            "seller_id": "s1",
            "price": [100.0, 200.0, 50.0, 80.0, 30.0, 40.0, 999.0],
            "freight_value": [10.0, 20.0, 10.0, 10.0, 5.0, 5.0, 1.0],
        }
    )
    payments = pd.DataFrame(
        {
            "order_id": ["j1", "j2", "a1", "a2", "a3", "a4"],
            "payment_type": [
                "credit_card",
                "boleto",
                "credit_card",
                "credit_card",
                "boleto",
                "voucher",
            ],
            "payment_installments": 1,
            "payment_value": [110.0, 220.0, 60.0, 90.0, 80.0, 1000.0],
        }
    )
    reviews = pd.DataFrame(
        {
            "review_id": ["r1", "r2", "r3", "r4", "r5"],
            "order_id": ["j1", "j2", "a1", "a2", "a3"],
            "review_score": [5, 4, 1, 5, 3],
            "review_answer_timestamp": pd.to_datetime(
                ["2018-07-11", "2018-07-16", "2018-08-12", "2018-08-07", "2018-08-09"]
            ),
        }
    )
    customers = pd.DataFrame(
        {
            "customer_id": ["c1", "c2", "c3", "c4", "c5", "c6"],
            "customer_unique_id": ["u1", "u2", "u3", "u3", "u4", "u5"],
            "customer_state": ["SP", "RJ", "RJ", "SP", "SP", "MG"],
        }
    )
    products = pd.DataFrame(
        {"product_id": ["p1", "p2"], "product_category_name": ["beleza_saude", "telefonia"]}
    )
    categories = pd.DataFrame(
        {
            "product_category_name": ["beleza_saude", "telefonia"],
            "product_category_name_english": ["health_beauty", "telephony"],
        }
    )
    return {
        "orders": orders,
        "items": items,
        "payments": payments,
        "reviews": reviews,
        "customers": customers,
        "products": products,
        "categories": categories,
    }
