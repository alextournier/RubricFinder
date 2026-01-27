# Future Development Ideas

> **Convention**: When starting work on a feature, add `[WIP]` to its heading. Remove when done or abandoned.

## Translation Pipeline

### Translation Guidelines
Translations must stick closely to original wording — only add understandability, never remove details. The original terminology is important.

### Multiple Translation Versions
Could generate alternate translations using different expressions and synonyms to improve recall.

### Rubric Format Interpretation
Translator needs heuristics for parsing rubric structure before translating — nested paths, implicit context from parent rubrics, abbreviations, punctuation conventions.

### Translation Validation
Backwards check — verify translation quality by comparing back to original.

### Translation Confidence Scores
LLM translator should return confidence score — some rubrics are ambiguous or hard to interpret; flag low-confidence translations for review.

### Translation Cost Comparison ✓
Benchmark translation costs across different LLMs (Claude Haiku vs Sonnet, GPT-4o-mini vs GPT-4o, etc.) — compare quality vs cost tradeoffs for the full repertory (~74,600 rubrics).

Script: `scripts/compare_llm_costs.py` — run with `--sample N` to test on N rubrics. Results in `tests/translation_cost_comparison.xlsx`.

## Search & Embeddings

### Translation vs Original Comparison
Embed original rubrics separately and compare search performance against translation embeddings — measure whether translations actually improve semantic matching.

### Embedding Model Options
Current `all-MiniLM-L6-v2` via sentence-transformers requires PyTorch (~2GB). For self-hosted server (size less constrained): could use larger/better models (e.g., `all-mpnet-base-v2`, `e5-large`); local embedding avoids API latency/costs; rubric embeddings are pre-computed, only queries need runtime embedding.

### Embedding Model Comparison
Benchmark different models (MiniLM vs mpnet vs e5-large vs OpenAI) using test sentences — quantify recall/precision improvement to justify larger model overhead.

## Data & Display

### Remedy Count
Check if OOREP data includes number of remedies per rubric — could display in search results as relevance indicator.
