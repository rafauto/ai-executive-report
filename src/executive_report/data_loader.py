"""Load the Olist CSV files and validate their schema."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import OLIST_FILES

REQUIRED_COLUMNS = {
    "orders": [
        "order_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "items": ["order_id", "order_item_id", "product_id", "price", "freight_value"],
    "payments": ["order_id", "payment_type", "payment_installments", "payment_value"],
    "reviews": ["review_id", "order_id", "review_score"],
    "customers": ["customer_id", "customer_unique_id", "customer_state"],
    "products": ["product_id", "product_category_name"],
    "categories": ["product_category_name", "product_category_name_english"],
}

DATE_COLUMNS = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "reviews": ["review_creation_date", "review_answer_timestamp"],
}


class DataValidationError(ValueError):
    """Raised when a file is missing or lacks required columns."""


def load_table(data_dir: Path, name: str) -> pd.DataFrame:
    path = Path(data_dir) / OLIST_FILES[name]
    if not path.exists():
        raise DataValidationError(
            f"File not found: {path}. Run `python scripts/download_data.py` "
            "or use the sample in data/sample."
        )
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS[name] if c not in df.columns]
    if missing:
        raise DataValidationError(f"{path.name} is missing required columns: {missing}")
    for col in DATE_COLUMNS.get(name, []):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def load_olist(data_dir: str | Path) -> dict[str, pd.DataFrame]:
    """Load every table used by the report."""
    data_dir = Path(data_dir)
    return {name: load_table(data_dir, name) for name in REQUIRED_COLUMNS}
