# Future Development Ideas

> **Convention**: When starting work on a feature, add `[WIP]` to its heading. Remove when done or abandoned.

## Translation Pipeline

### Translation Guidelines
Translations must stick closely to original wording — only add understandability, never remove details. The original terminology is important.

### Multiple Translation Versions
Could generate alternate translations using different expressions and synonyms to improve recall.

### Rubric Format Interpretation ✓
Heuristics added to translation prompt in `scripts/translate_rubrics.py`:
- Comma-separated hierarchy (general → specific)
- "of" suffix refers back to parent rubric
- Abbreviations: agg. (worse from), amel. (better from)
- Time/condition modifiers
- Subrubrics inherit parent context
- "ailments after X" = symptoms CAUSED BY event X (not tendency toward X)
- "speech, answers, ..." = specifically about answering questions
- Archaic word order warnings (e.g., "stabbed, so that he could have")
- ", after" suffix = what happens AFTER preceding event

### Translation Validation ✓
LLM judge script `scripts/judge_translations.py` scores translations on:
- Detail preservation (1-5)
- Accuracy (1-5)
- Clarity (1-5)

Run: `python scripts/judge_translations.py` on cost comparison results.

### Translation Confidence Scores
LLM translator should return confidence score — some rubrics are ambiguous or hard to interpret; flag low-confidence translations for review.

### Translation Cost Comparison ✓
Benchmark translation costs across different LLMs (Claude Haiku vs Sonnet, GPT-4o-mini vs GPT-4o, etc.) — compare quality vs cost tradeoffs for the full repertory (~74,600 rubrics).

Script: `scripts/compare_llm_costs.py` — run with `--sample N` to test on N rubrics. Results in `tests/translation_cost_comparison.xlsx`.

### API Rate Limits (Production Consideration)

OpenAI gpt-4o-mini has a **10,000 requests/day** limit on basic tiers. Translating 20K rubrics hit this limit multiple times.

**Mitigation strategies for production:**
- **Upgrade OpenAI tier** — Higher spending tiers get higher rate limits
- **Use OpenAI Batch API** — 50% cheaper, higher limits, but async (24h turnaround)
- **Multi-provider fallback** — Switch to Claude API when OpenAI quota exhausted
- **Pre-compute all translations** — Run translation offline, store results; no runtime API calls needed
- **Add retry with exponential backoff** — Handle transient 429 errors gracefully

**Current script behavior:** On 429 rate limit, waits 60s and retries indefinitely (sliding quota). On 5xx server errors, retries after 5s. Non-retryable errors are logged and skipped.

## Search & Embeddings

### Translation vs Original Comparison
Embed original rubrics separately and compare search performance against translation embeddings — measure whether translations actually improve semantic matching.

### Embedding Model Options
Current `all-MiniLM-L6-v2` via sentence-transformers requires PyTorch (~2GB). For self-hosted server (size less constrained): could use larger/better models (e.g., `all-mpnet-base-v2`, `e5-large`); local embedding avoids API latency/costs; rubric embeddings are pre-computed, only queries need runtime embedding.

### Embedding Model Comparison
Benchmark different models (MiniLM vs mpnet vs e5-large vs OpenAI) using test sentences — quantify recall/precision improvement to justify larger model overhead.

## Data & Display

### Remedy Count ✓
Search results now display remedy count (number of associated remedies per rubric). Extracted from OOREP data during rubric extraction.
