# ADR 0001: The LLM writes the narrative; code calculates every number

- **Status:** accepted
- **Date:** 2026-11-02

## Context

The report goes to leadership. LLMs make arithmetic mistakes and sometimes state invented numbers with confidence. One wrong number in an executive report costs more credibility than the time the automation saves.

## Decision

Python computes every KPI, comparison and alert. The LLM receives these values as JSON and only writes four fixed sections. Tables are rendered by Python, never by the LLM. A guardrail compares every R$ and % value in the AI text with the computed data and flags mismatches in the report.

## Consequences

- ✅ Numbers are tested and reproducible; the AI cannot change a table.
- ✅ The LLM prompt is small and cheap (a few thousand tokens per report).
- ⚠️ The LLM cannot answer questions the data package doesn't cover; new insights need new KPIs in code first.
- ⚠️ The guardrail checks values, not reasoning: interpretation still needs human review.

## Alternatives considered

- **Let the LLM read the CSVs and compute everything** (e.g. code interpreter): flexible, but slower, more expensive and much harder to trust and test.
- **No LLM, template text only**: reliable, but the text is repetitive and doesn't explain causes or recommend actions. It is kept as the `offline` mode.
