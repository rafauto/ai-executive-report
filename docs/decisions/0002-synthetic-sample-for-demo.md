# ADR 0002: Ship a synthetic sample instead of the real dataset

- **Status:** accepted
- **Date:** 2026-11-02

## Context

The public demo, the tests and CI need data. The Olist dataset is about 120 MB, requires a Kaggle account to download and is licensed CC BY-NC-SA 4.0.

## Decision

`scripts/generate_sample_data.py` creates a deterministic synthetic sample (seed 42, 10,000 orders, ~6 MB) with the exact Olist schema. It is committed in `data/sample/`. Its last complete month has deliberate problems so that alerts appear in the demo. Real data goes in `data/raw/`, which is git-ignored, and the pipeline prefers it when present.

## Consequences

- ✅ The demo and CI work with one click, no account and no download.
- ✅ No licensing questions about redistributing the dataset.
- ⚠️ Sample numbers are fictitious; the README and the app say so clearly.
- ⚠️ The generator must follow any schema change in the pipeline.

## Alternatives considered

- **Commit a subset of the real data:** realistic, but redistributes licensed data.
- **Download from Kaggle in CI and on Streamlit Cloud:** needs secrets everywhere and breaks when Kaggle is unavailable.
