# CLAUDE.md

Guidance for working on this repository with Claude Code.

## Project

Monthly executive report for the public Olist e-commerce dataset. Python computes KPIs and
alerts; an LLM only writes the narrative. The generated report is in Brazilian Portuguese;
code, comments, docs and commits are in English.

## Commands

```bash
pip install -e ".[dev,app]"                    # install
pytest                                         # tests (offline, LLM calls are mocked)
ruff check . && ruff format --check .          # lint + formatting
executive-report --provider offline            # generate a report without an API key
streamlit run app.py                           # web app
python scripts/run_eval.py --provider offline  # narrative evaluation (target 80%)
python scripts/record_responses.py --provider anthropic  # refresh demo answers (needs a key)
python scripts/generate_sample_data.py         # rebuild data/sample (synthetic)
mmdc -i docs/architecture.mmd -o docs/architecture.png -b white   # re-render the diagram
```

## Rules

- **The LLM never computes numbers.** New KPIs go in `kpis.py` with tests; the prompt only
  receives precomputed values. Keep the `guardrail.unverified_numbers` check working.
- LLM providers implement `NarrativeWriter` in `llm.py`; only that module imports an SDK.
- Alert rules live in `alerts.py`; thresholds in `AlertThresholds` (`config.py`).
- Report text uses Brazilian number format (`1.234,56`, `12,3%`) via `formatting.py`.
- Tests must run offline: inject `tests/helpers.FakeWriter`, use `tests/fixtures/` or mock the SDK module.
  Every bug fix gets a regression test.
- Never commit `.env`, `.streamlit/secrets.toml` or files in `data/raw/`.
- Only public or synthetic data. Do not mention employers or clients anywhere.
- Conventional Commits in English. Run ruff and pytest before each commit.
- When the structure changes, update the Mermaid diagram in the README and
  `docs/architecture.mmd`, and add an entry to `CHANGELOG.md`.

## Layout

- `src/executive_report/`: `data_loader` → `cleaning` → `kpis` → `alerts` → `llm` →
  `guardrail` → `report`, orchestrated by `pipeline.py`; `evaluation.py` scores narratives
- `app.py`: Streamlit app · `scripts/`: data download, sample generator, benchmark, eval
- `tests/`: pytest · `examples/`: sample output · `docs/`: architecture, ADRs, product brief
