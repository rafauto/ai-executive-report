"""Central settings: paths, file names, alert thresholds and time baselines."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
SAMPLE_DATA_DIR = PROJECT_ROOT / "data" / "sample"
REPORTS_DIR = PROJECT_ROOT / "reports"

# File names exactly as published on Kaggle (olistbr/brazilian-ecommerce).
OLIST_FILES = {
    "orders": "olist_orders_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "categories": "product_category_name_translation.csv",
}

# Baseline used to measure time saved (minutes per report).
# Adjust to your own process; see docs/time-measurement.md.
BASELINE_MANUAL_MIN = 300  # fully manual process (spreadsheets + writing): 5 h
BASELINE_AUTOMATION_MIN = 60  # previous automation (scripts, manual writing): 1 h
HUMAN_REVIEW_MIN = 10  # human review of the AI-generated report

# Cost guardrail for the public demo: LLM reports a visitor can generate per session.
MAX_LLM_REPORTS_PER_SESSION = int(os.getenv("MAX_LLM_REPORTS_PER_SESSION", "5"))


@dataclass(frozen=True)
class AlertThresholds:
    """Limits that trigger alerts. Tune them to the business reality."""

    revenue_drop_pct: float = -10.0  # month-over-month revenue drop (%)
    orders_drop_pct: float = -10.0  # month-over-month order drop (%)
    late_delivery_pct: float = 10.0  # % of deliveries after the promised date
    cancel_rate_pct: float = 2.0  # % of canceled/unavailable orders
    min_review_score: float = 4.0  # minimum acceptable average score (1-5)
    negative_review_pct: float = 15.0  # % of reviews scoring 1 or 2
    category_drop_pct: float = -25.0  # revenue drop of a top-5 category
    state_late_pct: float = 20.0  # % of late deliveries within a state
    min_state_orders: int = 50  # minimum delivered orders to evaluate a state


@dataclass(frozen=True)
class LLMSettings:
    """LLM provider settings, read from environment variables by default."""

    provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "anthropic").lower())
    model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", ""))
    temperature: float = field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.2")))
    max_tokens: int = field(default_factory=lambda: int(os.getenv("LLM_MAX_TOKENS", "2000")))
    timeout_s: float = field(default_factory=lambda: float(os.getenv("LLM_TIMEOUT", "60")))
    max_retries: int = field(default_factory=lambda: int(os.getenv("LLM_MAX_RETRIES", "2")))
    # Explicit key (e.g. typed into the app). When empty, the SDK reads the env var.
    api_key: str | None = field(default=None, repr=False)

    DEFAULT_MODELS = {
        "anthropic": "claude-sonnet-5-5",
        "openai": "gpt-4o-mini",
    }

    @property
    def resolved_model(self) -> str:
        return self.model or self.DEFAULT_MODELS.get(self.provider, "")


def load_env() -> None:
    """Load a local .env file when python-dotenv is installed (no-op otherwise)."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(PROJECT_ROOT / ".env")


def resolve_data_dir(explicit: str | Path | None = None) -> Path:
    """Use the given folder, else data/raw (real data), else data/sample."""
    if explicit:
        return Path(explicit)
    if (RAW_DATA_DIR / OLIST_FILES["orders"]).exists():
        return RAW_DATA_DIR
    return SAMPLE_DATA_DIR
