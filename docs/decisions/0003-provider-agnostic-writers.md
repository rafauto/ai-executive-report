# ADR 0003: Provider-agnostic narrative writers

- **Status:** accepted
- **Date:** 2026-11-02

## Context

LLM prices, quotas and quality change often. People trying the project may have a key for one provider and not another, or want to run a local model. Tests must run offline.

## Decision

Every provider implements the same `NarrativeWriter` interface (`write(data, alerts) -> LLMResult`). There are four writers: Anthropic (Claude), OpenAI-compatible (covers OpenAI, Groq, Gemini and Ollama through `OPENAI_BASE_URL`), recorded (replays real answers saved for the demo data) and offline (rule-based). `create_writer(settings)` picks one from configuration; `run_pipeline` also accepts an injected writer. Provider errors become a `NarrativeError` with a clear message; the app can fall back to the offline writer.

## Consequences

- ✅ Switching provider is a configuration change, not a code change.
- ✅ Integration tests inject a fake writer; no SDK or network is needed.
- ✅ The demo keeps working when a provider is down or a key is missing.
- ⚠️ Provider-specific features (tool use, prompt caching) are not used, to keep the interface small.

## Alternatives considered

- **An LLM framework (LangChain, LiteLLM):** more providers out of the box, but a heavy dependency for one call per report.
- **Claude only:** simpler, but locks visitors and contributors to one paid provider.
