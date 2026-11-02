# Contributing

Thanks for your interest! Contributions are welcome: bug fixes, new KPIs, new alert rules, new LLM providers or documentation improvements.

## Opening an issue

Before opening one, search the [existing issues](../../issues) to avoid duplicates. Then include:

- what you expected and what happened;
- the command you ran and the full error message;
- your Python version and operating system;
- whether you used the real data (`data/raw`) or the sample (`data/sample`).

**Never paste API keys in issues or pull requests.**

## Submitting a pull request

1. Fork the repository and create a branch from `main`:
   ```bash
   git checkout -b feat/short-description
   ```
2. Install the development dependencies:
   ```bash
   pip install -e ".[dev,app]"
   ```
3. Make your change **with tests** in `tests/`. Tests must run offline: mock any API call.
4. Make sure everything passes:
   ```bash
   ruff format .
   ruff check .
   pytest
   ```
5. Open the pull request explaining what changed and why. Link the related issue, if any.

## Commit messages

This project follows [Conventional Commits](https://www.conventionalcommits.org/), in English:

| Type | When to use it | Example |
|---|---|---|
| `feat` | new feature | `feat: add high-freight alert` |
| `fix` | bug fix | `fix: compare delivery dates by day` |
| `docs` | documentation only | `docs: explain Streamlit Cloud deploy` |
| `test` | tests | `test: cover month without previous data` |
| `refactor` | code change with no behavior change | `refactor: extract number formatting` |
| `style` | formatting only | `style: apply ruff format` |
| `ci` / `chore` | CI, dependencies, maintenance | `ci: add Python 3.13 to the matrix` |

## Project principles

- **The AI never calculates numbers.** Every new indicator is computed in `kpis.py` and tested; the LLM only writes.
- Report text is in Brazilian Portuguese, with numbers formatted as `1.234,56` (see `formatting.py`).
- New alert rules go in `alerts.py`, with a configurable threshold in `AlertThresholds`.
- Only public or synthetic data.
