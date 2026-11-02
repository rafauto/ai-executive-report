# Contributing

Thanks for your interest! Contributions are welcome: bug fixes, new KPIs, new alert rules, new LLM providers or documentation improvements.

> ⚠️ **Never paste real data, personal data or API keys** in issues, pull requests, commits or test fixtures. Use the synthetic sample (`data/sample/`) or made-up values. If a key is ever committed, revoke it immediately: deleting the commit is not enough.

## Opening an issue

1. Search the [existing issues](../../issues) to avoid duplicates.
2. Choose a template:
   - **Bug report**: what happened, what you expected, how to reproduce it, the full error and your environment.
   - **Feature request**: a user story ("As a … I want … so that …") with acceptance criteria.

## Submitting a pull request

1. Fork the repository and create a branch from `main`:
   ```bash
   git checkout -b feat/short-description
   ```
2. Install the development dependencies:
   ```bash
   pip install -e ".[dev,app]"
   ```
3. Make your change **with tests** in `tests/`. Tests must run offline: inject a fake writer or mock the SDK. A bug fix needs a regression test.
4. Run lint and tests before opening the pull request:
   ```bash
   ruff format .
   ruff check .
   pytest
   ```
   If you changed the prompt or a writer, also run `python scripts/run_eval.py` and paste the result in the pull request.
5. Open the pull request with the template: what changed, why, and the issue it closes. It is merged only with a green CI.

## Commit messages

This project follows [Conventional Commits](https://www.conventionalcommits.org/), in English. One logical change per commit:

| Type | When to use it | Example |
|---|---|---|
| `feat` | new feature | `feat: add high-freight alert` |
| `fix` | bug fix | `fix: compare delivery dates by day` |
| `docs` | documentation only | `docs: explain Streamlit Cloud deploy` |
| `test` | tests | `test: cover month without previous data` |
| `refactor` | code change with no behavior change | `refactor: extract number formatting` |
| `style` | formatting only | `style: apply ruff format` |
| `ci` / `chore` | CI, dependencies, maintenance | `ci: add Python 3.13 to the matrix` |

## Guiding principles

- **The AI never calculates numbers.** Every new indicator is computed in `kpis.py` and tested; the LLM only writes ([ADR 0001](docs/decisions/0001-llm-writes-code-calculates.md)).
- **External services stay behind an interface.** New LLM providers implement `NarrativeWriter`; nothing else imports an SDK.
- **Keep it simple.** The simplest solution that solves the problem; no layers or tools "for the future".
- **Configuration, not constants.** Keys, URLs and limits come from environment variables or `config.py`.
- **Only public or synthetic data**, and no company names anywhere in the repository.
- Report text is in Brazilian Portuguese with Brazilian number format (`formatting.py`); everything else is in English.
- Update the README, the architecture diagram and the CHANGELOG when the structure or behavior changes.
