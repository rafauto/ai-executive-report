# Product brief

## Problem

E-commerce managers lose about five hours every month turning raw order data into an executive report, because indicators, alerts and the written analysis are all assembled by hand.

## Target user

**Persona: the operations or e-commerce manager** who presents monthly results to leadership. They know the business well, have little time, work from spreadsheets and need to explain *what changed and what to do about it*, not just show numbers.

Secondary user: the analyst who prepares the numbers and wants to stop rewriting the same narrative every month.

## Success criteria

| Criterion | Target | How it is measured |
|---|---|---|
| Automated generation time | under 2 minutes | `stage_seconds` in `reports/metrics_YYYY-MM.json` |
| Total time per report, with human review | 15 minutes or less (baseline: 5 h manual, 1 h scripted) | benchmark + timed review (`docs/time-measurement.md`) |
| Number accuracy | 0 numbers in the AI text that are not in the data | guardrail (`unverified_numbers`) |
| Narrative quality | ≥ 80% of eval cases passing | `scripts/run_eval.py` |

## MVP scope

**In:** load and clean the Olist orders, 10 monthly KPIs vs. the previous month, rule-based alerts, an LLM-written narrative with a number check, a Markdown report and a CLI.

**Out (roadmap):** PDF and scheduled email, revenue forecast, review sentiment analysis, order-level drill-down. The Streamlit app and the key-less demo mode were added after the MVP so people can try it without installing anything.

## Hypothesis

We believe that **computing KPIs and alerts in code and letting an LLM write only the narrative** solves **the hours lost assembling the monthly executive report** for **e-commerce managers**. We will know it works when **a report takes 15 minutes or less including review, with zero unverified numbers and an eval pass rate of at least 80%**.

## Validation

Plan: share a generated report with at least one person who fits the persona and ask three questions.

1. Could you present this report as it is? If not, what would you change?
2. Which alert or recommendation would you act on first?
3. What is missing that you would normally add by hand?

<!-- TODO: log each feedback session below (date, persona, main findings, backlog changes). -->

| Date | Persona | Main findings | Backlog changes |
|---|---|---|---|
