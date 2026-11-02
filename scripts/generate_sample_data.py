"""Generate a SYNTHETIC sample with the same schema as the Olist dataset.

It lets the demo (Streamlit Cloud, CI and tests) run without downloading the
~120 MB Kaggle dataset. The numbers are NOT real: for a real analysis use the
original data (`python scripts/download_data.py`).

The sample deliberately includes a few problems in the latest complete month
(late deliveries in RJ and BA, lower volume) so that alerts show up in the demo.

Usage:
    python scripts/generate_sample_data.py --orders 10000 --seed 42
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from executive_report.config import OLIST_FILES, SAMPLE_DATA_DIR  # noqa: E402

STATES = {
    "SP": 0.42,
    "RJ": 0.13,
    "MG": 0.12,
    "RS": 0.055,
    "PR": 0.05,
    "SC": 0.037,
    "BA": 0.034,
    "DF": 0.021,
    "GO": 0.02,
    "ES": 0.02,
    "PE": 0.017,
    "CE": 0.013,
    "PA": 0.01,
    "MT": 0.009,
    "MA": 0.008,
}
CATEGORIES = {
    "cama_mesa_banho": ("bed_bath_table", 0.11, 95),
    "beleza_saude": ("health_beauty", 0.10, 130),
    "esporte_lazer": ("sports_leisure", 0.09, 115),
    "moveis_decoracao": ("furniture_decor", 0.085, 110),
    "informatica_acessorios": ("computers_accessories", 0.08, 140),
    "utilidades_domesticas": ("housewares", 0.075, 90),
    "relogios_presentes": ("watches_gifts", 0.07, 200),
    "telefonia": ("telephony", 0.06, 70),
    "ferramentas_jardim": ("garden_tools", 0.055, 105),
    "automotivo": ("auto", 0.05, 125),
    "brinquedos": ("toys", 0.05, 100),
    "cool_stuff": ("cool_stuff", 0.04, 160),
    "perfumaria": ("perfumery", 0.04, 120),
    "bebes": ("baby", 0.035, 125),
    "eletronicos": ("electronics", 0.03, 80),
    "papelaria": ("stationery", 0.03, 85),
}
STATE_BASE_DAYS = {
    "SP": 8,
    "RJ": 14,
    "MG": 11,
    "RS": 14,
    "PR": 11,
    "SC": 14,
    "BA": 18,
    "DF": 12,
    "GO": 14,
    "ES": 15,
    "PE": 17,
    "CE": 20,
    "PA": 23,
    "MT": 17,
    "MA": 21,
}


def _hex_ids(rng: np.random.Generator, n: int) -> np.ndarray:
    raw = rng.integers(0, 2**63, size=(n, 2), dtype=np.int64)
    return np.array([f"{a:016x}{b:016x}" for a, b in raw])


def generate(n_orders: int, seed: int) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)

    # Growing volume from Jan/2017 to Aug/2018 + a short Sep/Oct 2018 tail (as in the real data).
    months = pd.period_range("2017-01", "2018-08", freq="M")
    weights = np.linspace(1.0, 3.2, len(months))
    weights[-3:-1] *= 1.05  # Jun-Jul/2018 slightly stronger
    weights[-1] *= 0.86  # Aug/2018: volume drop to trigger an alert
    weights = weights / weights.sum()
    n_tail = max(5, n_orders // 400)
    month_of_order = rng.choice(len(months), size=n_orders - n_tail, p=weights)
    purchase = []
    for mi in month_of_order:
        start = months[mi].start_time
        purchase.append(
            start + pd.Timedelta(seconds=int(rng.integers(0, months[mi].days_in_month * 86400)))
        )
    for _ in range(n_tail):
        purchase.append(pd.Timestamp("2018-09-01") + pd.Timedelta(days=int(rng.integers(0, 45))))
    purchase = pd.to_datetime(purchase)
    n = len(purchase)
    last_month = purchase.to_period("M") == pd.Period("2018-08", "M")

    order_ids = _hex_ids(rng, n)
    customer_ids = _hex_ids(rng, n)
    # ~3% returning customers
    unique_pool = _hex_ids(rng, int(n * 0.97))
    customer_unique = rng.choice(unique_pool, size=n)
    states = rng.choice(
        list(STATES), size=n, p=np.array(list(STATES.values())) / sum(STATES.values())
    )

    status = rng.choice(
        ["delivered", "shipped", "canceled", "unavailable", "invoiced", "processing"],
        size=n,
        p=[0.967, 0.011, 0.007, 0.006, 0.005, 0.004],
    )
    # Final tail: recent orders not delivered yet
    status[purchase >= pd.Timestamp("2018-09-01")] = "shipped"
    # Aug/2018: slightly more cancellations
    bump = last_month & (rng.random(n) < 0.012)
    status[bump] = "canceled"

    approved = purchase + pd.to_timedelta(rng.exponential(0.4, n), unit="D")
    carrier = approved + pd.to_timedelta(rng.gamma(2, 1.4, n), unit="D")
    base = np.array([STATE_BASE_DAYS[s] for s in states], dtype=float)
    delivery_days = rng.gamma(4, base / 4)
    estimated_days = base * 1.9 + rng.integers(3, 10, n)
    # Anomaly: logistics bottleneck in RJ and BA in Aug/2018
    shock = last_month & np.isin(states, ["RJ", "BA"])
    delivery_days[shock] *= 2.1
    delivery_days[last_month & ~shock] *= 1.15
    delivered = purchase + pd.to_timedelta(delivery_days, unit="D")
    estimated = (purchase + pd.to_timedelta(estimated_days, unit="D")).normalize()

    not_delivered = status != "delivered"
    orders = pd.DataFrame(
        {
            "order_id": order_ids,
            "customer_id": customer_ids,
            "order_status": status,
            "order_purchase_timestamp": purchase,
            "order_approved_at": approved,
            "order_delivered_carrier_date": carrier.where(
                ~np.isin(status, ["canceled", "unavailable", "processing"])
            ),
            "order_delivered_customer_date": delivered.where(~not_delivered),
            "order_estimated_delivery_date": estimated,
        }
    )

    # Products
    cat_names = list(CATEGORIES)
    cat_p = np.array([v[1] for v in CATEGORIES.values()])
    cat_p = cat_p / cat_p.sum()
    n_products = max(300, n // 6)
    product_ids = _hex_ids(rng, n_products)
    product_cat = rng.choice(cat_names, size=n_products, p=cat_p)
    products = pd.DataFrame(
        {
            "product_id": product_ids,
            "product_category_name": product_cat,
            "product_name_lenght": rng.integers(20, 64, n_products),
            "product_description_lenght": rng.integers(100, 3000, n_products),
            "product_photos_qty": rng.integers(1, 6, n_products),
            "product_weight_g": rng.integers(100, 15000, n_products),
            "product_length_cm": rng.integers(15, 80, n_products),
            "product_height_cm": rng.integers(2, 60, n_products),
            "product_width_cm": rng.integers(10, 60, n_products),
        }
    )
    by_cat = {c: product_ids[product_cat == c] for c in cat_names}

    # Items
    n_items = rng.choice([1, 2, 3, 4], size=n, p=[0.88, 0.08, 0.03, 0.01])
    seller_ids = _hex_ids(rng, max(80, n // 40))
    rows = []
    for i in range(n):
        cat = rng.choice(cat_names, p=cat_p)
        # Anomaly: watches & gifts lose about half of their demand in Aug/2018
        if last_month[i] and cat == "relogios_presentes" and rng.random() < 0.55:
            cat = "utilidades_domesticas"
        pid = rng.choice(by_cat[cat])
        mean_price = CATEGORIES[cat][2]
        price = round(float(rng.lognormal(np.log(mean_price), 0.7)), 2)
        seller = rng.choice(seller_ids)
        for k in range(1, n_items[i] + 1):
            freight = round(float(np.clip(rng.normal(18 + 0.06 * price, 6), 0, None)) + 4, 2)
            rows.append(
                (order_ids[i], k, pid, seller, purchase[i] + pd.Timedelta(days=6), price, freight)
            )
    items = pd.DataFrame(
        rows,
        columns=[
            "order_id",
            "order_item_id",
            "product_id",
            "seller_id",
            "shipping_limit_date",
            "price",
            "freight_value",
        ],
    )

    # Payments
    totals = items.groupby("order_id")[["price", "freight_value"]].sum().sum(axis=1)
    ptype = rng.choice(
        ["credit_card", "boleto", "voucher", "debit_card"], size=n, p=[0.74, 0.19, 0.055, 0.015]
    )
    installments = np.where(ptype == "credit_card", rng.choice(range(1, 11), size=n), 1)
    payments = pd.DataFrame(
        {
            "order_id": order_ids,
            "payment_sequential": 1,
            "payment_type": ptype,
            "payment_installments": installments,
            "payment_value": totals.reindex(order_ids).round(2).to_numpy(),
        }
    )

    # Reviews: scores get worse when delivery is late
    late = (delivered.normalize() > estimated) & ~not_delivered
    p_good = [0.05, 0.03, 0.08, 0.20, 0.64]
    p_late = [0.40, 0.12, 0.15, 0.15, 0.18]
    scores = np.where(
        late, rng.choice(range(1, 6), size=n, p=p_late), rng.choice(range(1, 6), size=n, p=p_good)
    )
    scores = np.where(np.isin(status, ["canceled", "unavailable"]), 1, scores)
    has_review = rng.random(n) < 0.99
    review_dates = (
        delivered.where(~not_delivered, purchase + pd.Timedelta(days=20))
    ).normalize() + pd.Timedelta(days=1)
    reviews = pd.DataFrame(
        {
            "review_id": _hex_ids(rng, n),
            "order_id": order_ids,
            "review_score": scores,
            "review_comment_title": None,
            "review_comment_message": None,
            "review_creation_date": review_dates,
            "review_answer_timestamp": review_dates
            + pd.to_timedelta(rng.exponential(2, n), unit="D"),
        }
    )[has_review]

    customers = pd.DataFrame(
        {
            "customer_id": customer_ids,
            "customer_unique_id": customer_unique,
            "customer_zip_code_prefix": rng.integers(1000, 99999, n),
            "customer_city": "cidade",
            "customer_state": states,
        }
    )
    categories = pd.DataFrame(
        [(k, v[0]) for k, v in CATEGORIES.items()],
        columns=["product_category_name", "product_category_name_english"],
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--orders", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=SAMPLE_DATA_DIR)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    for name, df in generate(args.orders, args.seed).items():
        path = args.out / OLIST_FILES[name]
        df.to_csv(path, index=False, date_format="%Y-%m-%d %H:%M:%S")
        print(f"{path.relative_to(ROOT)}: {len(df):,} rows")


if __name__ == "__main__":
    main()
