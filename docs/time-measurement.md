# Measuring the time saved

## Baseline

| Process | Time | How it was measured |
|---|---:|---|
| Manual | 5 h | average of reports built by hand (spreadsheets, joins, charts and writing) |
| Previous automation | 1 h | scripts computed the numbers; analysis and writing were manual |
| With AI | measured generation + review | pipeline stopwatch + estimated human review |

The values live in `src/executive_report/config.py` (`BASELINE_MANUAL_MIN`, `BASELINE_AUTOMATION_MIN`, `HUMAN_REVIEW_MIN`). Adjust them to your own numbers.

## How to measure

1. Every run saves the seconds per stage to `reports/metrics_YYYY-MM.json` (see [an example](../examples/metrics_2018-08_sample_offline.json)):
   ```json
   {
     "stage_seconds": {"1_load_data": 0.14, "2_clean": 0.15, "...": 0},
     "total_seconds": 0.35,
     "llm": {"provider": "offline", "input_tokens": null, "output_tokens": null}
   }
   ```
2. For the README, run the benchmark on the real data with the LLM enabled:
   ```bash
   python scripts/benchmark.py --runs 5 --provider anthropic
   ```
   It prints two Markdown tables (time per stage and comparison with the baseline), ready to paste.
3. Also time your **review** of 2 or 3 generated reports and update `HUMAN_REVIEW_MIN` with the average.

## Formula

```
ai_minutes            = total_seconds / 60 + HUMAN_REVIEW_MIN
saved_vs_manual       = 1 - ai_minutes / BASELINE_MANUAL_MIN
saved_vs_automation   = 1 - ai_minutes / BASELINE_AUTOMATION_MIN
```

Example: 30 s of generation + 10 min of review = 10.5 min, which is 96.5% less than the manual process and 82.5% less than the previous automation. Over a year (12 reports), that is about 58 hours saved compared with the manual process.
