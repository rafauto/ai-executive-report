# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-11-02

### Added
- `NarrativeWriter` interface with Anthropic, OpenAI-compatible and offline writers.
- LLM timeouts, retries and a clear `NarrativeError` for provider failures.
- Offline fallback in the Streamlit app when the AI provider fails (failures are not cached).
- Per-session limit of AI reports in the public demo (`MAX_LLM_REPORTS_PER_SESSION`).
- Evaluation harness (`scripts/run_eval.py`) with five fixed cases and five quality checks.
- Input validation for the reference month and sanitized category labels (prompt-injection defense).
- Prompt rule to treat the JSON payload as data only.
- Integration, regression and Streamlit smoke tests; eval smoke test in CI.
- Dependabot, issue and pull request templates, ADRs, product brief and this changelog.
- `--verbose` flag with logging in the CLI.

### Changed
- Number guardrail moved to its own module (`guardrail.py`).
- Ruff now uses the shared configuration (`E, F, W, I, UP, B`, line length 100).

### Removed
- Unused columns from the cleaned order view.

## [0.1.0] - 2026-11-02

MVP: the main flow works end to end.

### Added
- Load and validate the Olist CSVs; clean them into one row per order.
- 10 monthly KPIs with month-over-month comparison and rule-based alerts.
- LLM narrative (Claude or OpenAI-compatible) with a number guardrail; offline mode.
- Markdown report, CLI with per-stage timing, benchmark script and Streamlit app.
- Synthetic sample data, offline test suite and CI on Python 3.10 and 3.12.

### Fixed
- Signed absolute changes in the KPI table (`+3,8` instead of `3,80`).
- A visitor's API key is never written to `os.environ`, which is shared across app sessions.

[1.0.0]: https://github.com/YOUR_GITHUB_USERNAME/ai-executive-report/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/YOUR_GITHUB_USERNAME/ai-executive-report/releases/tag/v0.1.0
