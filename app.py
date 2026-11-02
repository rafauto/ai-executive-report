"""Streamlit demo for the AI Executive Report.

Run locally:  streamlit run app.py
"""

from __future__ import annotations

import os
import sys
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from executive_report.cleaning import build_orders_view, latest_complete_month  # noqa: E402
from executive_report.config import (  # noqa: E402
    BASELINE_AUTOMATION_MIN,
    BASELINE_MANUAL_MIN,
    HUMAN_REVIEW_MIN,
    MAX_LLM_REPORTS_PER_SESSION,
    RAW_DATA_DIR,
    SAMPLE_DATA_DIR,
    LLMSettings,
    load_env,
)
from executive_report.data_loader import load_olist  # noqa: E402
from executive_report.formatting import brl, num, pct  # noqa: E402
from executive_report.llm import NarrativeError, RecordedWriter  # noqa: E402
from executive_report.pipeline import run_pipeline  # noqa: E402

st.set_page_config(page_title="AI Executive Report · Olist", page_icon="📊", layout="wide")
load_env()  # local .env, if present

# Streamlit Cloud secrets become environment variables for the SDKs.
for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENAI_BASE_URL", "LLM_PROVIDER", "LLM_MODEL"):
    try:
        if key in st.secrets and not os.getenv(key):
            os.environ[key] = str(st.secrets[key])
    except Exception:  # no local secrets.toml: rely on .env / environment
        break


@st.cache_data(show_spinner="Loading and cleaning the data...")
def load_view(data_dir: str) -> pd.DataFrame:
    return build_orders_view(load_olist(data_dir))


@st.cache_data(show_spinner="Generating the report...", ttl=24 * 3600)
def cached_report(data_dir: str, month: str, provider: str, model: str, _api_key: str | None):
    """Cached per month/provider so repeat visitors don't spend tokens again.

    The leading underscore tells Streamlit not to hash the key.
    """
    view = load_view(data_dir)
    settings = LLMSettings(provider=provider, model=model, api_key=_api_key)
    result = run_pipeline(data_dir, month, settings, view=view)
    return (
        result.markdown,
        result.data,
        result.alerts,
        asdict(result.llm),
        result.timings,
        result.unverified,
    )


# ---------------------------------------------------------------- sidebar
st.sidebar.title("⚙️ Settings")
sources = {"Synthetic sample (demo)": str(SAMPLE_DATA_DIR)}
if (RAW_DATA_DIR / "olist_orders_dataset.csv").exists():
    sources = {"Real Olist data (Kaggle)": str(RAW_DATA_DIR), **sources}
source_label = st.sidebar.selectbox("Dataset", list(sources))
data_dir = sources[source_label]

view = load_view(data_dir)
month_options = [str(m) for m in sorted(view["month"].unique())][1:]  # first month has no baseline
default_month = str(latest_complete_month(view))
month = st.sidebar.selectbox(
    "Reference month", month_options, index=month_options.index(default_month)
)

has_server_key = bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY"))
has_recordings = data_dir == str(SAMPLE_DATA_DIR) and bool(RecordedWriter().available_months())
provider_options = ["anthropic", "openai", "recorded", "offline"]
if has_server_key:
    default_provider = os.getenv("LLM_PROVIDER", "anthropic")
else:  # demo mode: no key needed
    default_provider = "recorded" if has_recordings else "offline"
provider = st.sidebar.selectbox(
    "AI provider",
    provider_options,
    index=provider_options.index(default_provider),
    help=(
        "'recorded' replays real AI answers saved for the sample data; "
        "'offline' writes the narrative with rules. Both are free."
    ),
)
model = st.sidebar.text_input(
    "Model (optional)",
    value=os.getenv("LLM_MODEL", ""),
    placeholder=LLMSettings.DEFAULT_MODELS.get(provider, ""),
)
user_key = ""
if provider in ("anthropic", "openai"):
    user_key = st.sidebar.text_input(
        "Your API key (optional)",
        type="password",
        help=(
            "Used only in this session and never stored. "
            "Without it, the server key is used, if any."
        ),
    )
    # The visitor's key NEVER goes into os.environ (which is shared across sessions).
    if not user_key and not has_server_key:
        st.sidebar.warning("No API key configured: choose 'offline' or enter your own key.")

st.sidebar.markdown("---")
st.sidebar.caption(
    "Data: [Olist Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)"
    " · CC BY-NC-SA 4.0"
)

# ---------------------------------------------------------------- main
st.title("📊 AI Executive Report")
st.caption(
    "A Python pipeline cleans Olist orders and computes KPIs and alerts; "
    "an LLM writes the executive report (in Brazilian Portuguese)."
)
if data_dir == str(SAMPLE_DATA_DIR):
    st.info(
        "You are viewing the **synthetic sample** (Olist schema, fictitious numbers).", icon="ℹ️"
    )

llm_runs = st.session_state.get("llm_runs", 0)
if st.button("🚀 Generate report", type="primary"):
    uses_paid_api = provider in ("anthropic", "openai")
    if uses_paid_api and llm_runs >= MAX_LLM_REPORTS_PER_SESSION:
        st.warning(
            f"This demo allows {MAX_LLM_REPORTS_PER_SESSION} AI reports per session to keep "
            "costs under control. Switch to 'recorded' or 'offline', or run it locally."
        )
        st.stop()
    if uses_paid_api:
        st.session_state["llm_runs"] = llm_runs + 1
    st.session_state["run"] = (data_dir, month, provider, model)

if "run" not in st.session_state:
    st.write("Pick a month and a provider in the sidebar, then click **Generate report**.")
    st.stop()

run_data_dir, run_month, run_provider, run_model = st.session_state["run"]
try:
    try:
        markdown, data, alerts, llm, timings, unverified = cached_report(
            run_data_dir, run_month, run_provider, run_model, user_key or None
        )
    except NarrativeError as exc:
        # Provider down or key invalid: keep the app useful with the offline narrative.
        # Failures are not cached, so the next click tries the AI again.
        st.warning(f"The AI narrative is unavailable, so it was written offline. {exc}")
        markdown, data, alerts, llm, timings, unverified = cached_report(
            run_data_dir, run_month, "offline", "", None
        )
except Exception as exc:
    st.error(f"Could not generate the report: {exc}")
    st.stop()

k, kp, change = data["kpis"], data["previous_kpis"], data["mom_change_pct"]
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Revenue", brl(k["revenue"]), pct(change["revenue"], signed=True))
c2.metric("Orders", num(k["orders"]), pct(change["orders"], signed=True))
c3.metric("Average ticket", brl(k["avg_ticket"]), pct(change["avg_ticket"], signed=True))
c4.metric(
    "Late deliveries",
    pct(k["late_delivery_pct"]),
    f"{k['late_delivery_pct'] - kp['late_delivery_pct']:+.1f} p.p.",
    delta_color="inverse",
)
c5.metric(
    "Avg. review score",
    num(k["avg_review_score"], 2),
    f"{(k['avg_review_score'] or 0) - (kp['avg_review_score'] or 0):+.2f}",
)

tab_report, tab_charts, tab_time, tab_data = st.tabs(
    ["📝 Report", "📈 Charts", "⏱️ Time saved", "🔎 Data"]
)

with tab_report:
    st.markdown(markdown)
    st.download_button(
        "⬇️ Download report (.md)", markdown, file_name=f"report_{data['reference_month']}.md"
    )

with tab_charts:
    series = pd.DataFrame(data["monthly_series"]).set_index("month")
    left, right = st.columns(2)
    left.subheader("Monthly revenue (R$)")
    left.line_chart(series["revenue"])
    right.subheader("Orders per month")
    right.bar_chart(series["orders"])
    st.subheader("Late deliveries by state (%)")
    states = pd.DataFrame(data["delivery_by_state"])
    if not states.empty:
        st.bar_chart(states.set_index("state")["late_pct"])

with tab_time:
    total_s = sum(timings.values())
    ai_min = total_s / 60 + HUMAN_REVIEW_MIN
    t1, t2, t3 = st.columns(3)
    t1.metric("Manual process", f"{BASELINE_MANUAL_MIN / 60:.0f} h")
    t2.metric("Previous automation", f"{BASELINE_AUTOMATION_MIN / 60:.0f} h")
    t3.metric(
        "With AI (generation + review)",
        f"{ai_min:.0f} min",
        f"-{100 * (1 - ai_min / BASELINE_MANUAL_MIN):.0f}% vs. manual",
        delta_color="inverse",
    )
    st.caption(
        f"Automated generation measured now: {total_s:.1f} s · "
        f"estimated human review: {HUMAN_REVIEW_MIN} min."
    )
    st.dataframe(
        pd.DataFrame({"stage": list(timings), "seconds": list(timings.values())}), hide_index=True
    )

with tab_data:
    st.subheader("Alerts (deterministic rules)")
    st.dataframe(pd.DataFrame(alerts), hide_index=True)
    st.subheader("Top categories")
    st.dataframe(pd.DataFrame(data["top_categories"]), hide_index=True)
    st.caption(f"Narrative: {llm['provider']} · model {llm['model']}")
    if unverified:
        st.warning(f"Numbers in the AI text that don't match the data: {', '.join(unverified)}")
