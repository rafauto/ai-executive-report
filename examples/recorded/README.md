# Recorded LLM answers

Real answers from an LLM, generated on the synthetic sample in `data/sample/` and replayed by
the `recorded` provider. They let the public demo show genuine AI text without an API key
and without any cost per visitor.

Create or refresh them with an API key configured:

```bash
python scripts/record_responses.py --provider anthropic
```

Each file stores the month, the recording date, the provider, the model, token counts and the
text. Answers whose numbers fail the guardrail are never saved. If `data/sample/` is
regenerated, record the answers again: they only match the dataset they were made from.
