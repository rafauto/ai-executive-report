"""Data cleaning: join the Olist tables into one row per order, ready for KPIs."""

from __future__ import annotations

import pandas as pd

CANCELED_STATUSES = {"canceled", "unavailable"}
MAX_LABEL_LENGTH = 60


def clean_label(series: pd.Series) -> pd.Series:
    """Readable, safe labels: letters, digits, spaces and hyphens only, length-capped.

    Category names end up in the LLM prompt, so anything that could carry
    instructions or markup is stripped here.
    """
    return (
        series.fillna("sem_categoria")
        .astype(str)
        .str.replace("_", " ")
        .str.replace(r"[^\w\s-]", "", regex=True)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
        .str.slice(0, MAX_LABEL_LENGTH)
        .replace("", "sem categoria")
    )


def _main_category(items: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    """Highest-value category in each order, with a readable name."""
    prod = products[["product_id", "product_category_name"]].copy()
    prod["category"] = clean_label(prod["product_category_name"])
    merged = items.merge(prod[["product_id", "category"]], on="product_id", how="left")
    merged["category"] = merged["category"].fillna("sem categoria")
    by_cat = merged.groupby(["order_id", "category"], as_index=False)["price"].sum()
    idx = by_cat.groupby("order_id")["price"].idxmax()
    return by_cat.loc[idx, ["order_id", "category"]]


def build_orders_view(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """One row per order with values, customer, delivery, review and category."""
    orders = tables["orders"].drop_duplicates("order_id").copy()
    orders = orders.dropna(subset=["order_purchase_timestamp"])

    items = tables["items"].copy()
    items[["price", "freight_value"]] = items[["price", "freight_value"]].clip(lower=0)
    item_totals = items.groupby("order_id").agg(
        items_value=("price", "sum"),
        freight_value=("freight_value", "sum"),
    )

    # Main payment method = the one with the largest amount in the order.
    main_payment = (
        tables["payments"]
        .sort_values("payment_value", ascending=False)
        .drop_duplicates("order_id")
        .set_index("order_id")[["payment_type"]]
    )

    # An order may have more than one review: keep the most recent one.
    reviews = tables["reviews"].copy()
    sort_col = "review_answer_timestamp" if "review_answer_timestamp" in reviews else "review_id"
    reviews = reviews.sort_values(sort_col).drop_duplicates("order_id", keep="last")
    reviews = reviews.set_index("order_id")[["review_score"]]

    customers = tables["customers"].set_index("customer_id")[
        ["customer_unique_id", "customer_state"]
    ]
    categories = _main_category(items, tables["products"]).set_index("order_id")

    view = (
        orders.set_index("order_id")
        .join(item_totals)
        .join(main_payment)
        .join(reviews)
        .join(categories)
        .reset_index()
        .merge(customers, left_on="customer_id", right_index=True, how="left")
    )

    view["order_value"] = view["items_value"].fillna(0) + view["freight_value"].fillna(0)
    view["month"] = view["order_purchase_timestamp"].dt.to_period("M")
    view["is_canceled"] = view["order_status"].isin(CANCELED_STATUSES)
    view["is_delivered"] = (
        view["order_status"].eq("delivered") & view["order_delivered_customer_date"].notna()
    )
    view["delivery_days"] = (
        view["order_delivered_customer_date"] - view["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400
    view.loc[~view["is_delivered"], "delivery_days"] = pd.NA
    view["is_late"] = view["is_delivered"] & (
        view["order_delivered_customer_date"].dt.normalize()
        > view["order_estimated_delivery_date"].dt.normalize()
    )
    view["category"] = view["category"].fillna("sem categoria")
    view["customer_state"] = view["customer_state"].fillna("ND")
    return view


def latest_complete_month(view: pd.DataFrame, min_share: float = 0.3) -> pd.Period:
    """Latest month with meaningful volume.

    The Olist dataset ends with almost empty months (Sep-Oct 2018); a month only
    counts if it has at least `min_share` of the median monthly order count.
    """
    counts = view.groupby("month").size().sort_index()
    threshold = counts.median() * min_share
    valid = counts[counts >= threshold]
    if valid.empty:
        raise ValueError("No month has enough orders to build a report.")
    return valid.index.max()
