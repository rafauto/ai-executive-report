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
python -m executive_report --provider offline  # generate a report without an API key
streamlit run app.py                           # web app
python scripts/generate_sample_data.py         # rebuild data/sample (synthetic)
```

## Rules

- **The LLM never computes numbers.** New KPIs go in `kpis.py` with tests; the prompt only
  receives precomputed values. Keep the `unverified_numbers` guardrail working.
- Alert rules live in `alerts.py`; thresholds in `AlertThresholds` (`config.py`).
- Report text uses Brazilian number format (`1.234,56`, `12,3%`) via `formatting.py`.
- Tests must run offline: mock `anthropic` / `openai` with `monkeypatch.setitem(sys.modules, ...)`.
- Never commit `.env`, `.streamlit/secrets.toml` or files in `data/raw/`.
- Only public or synthetic data. Do not mention employers or clients anywhere.
- Conventional Commits in English (`feat:`, `fix:`, `docs:`, `test:`, `ci:`, `chore:`,
  `style:`, `refactor:`). Run ruff and pytest before each commit.

## Layout

- `src/executive_report/`: pipeline (`data_loader` → `cleaning` → `kpis` → `alerts` →
  `llm` → `report`, orchestrated by `pipeline.py`)
- `app.py`: Streamlit app · `scripts/`: data download, sample generator, benchmark
- `tests/`: pytest · `examples/`: sample output · `docs/`: architecture and time measurement
