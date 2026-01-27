# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RubricFinder is a semantic search webapp for homeopathic rubrics. It extracts rubrics from the OOREP PostgreSQL dump, translates archaic rubric language to modern English using LLMs, embeds translations in Qdrant, and provides search via a web interface.

## Architecture

```
OOREP SQL dump → Extract rubrics → LLM translation → Embed in Qdrant → Streamlit frontend
```

Key components:
- **Data extraction**: Parse `oorep.sql.gz` to extract rubrics and remedy counts (starting with Mind chapter)
- **Translation pipeline**: LLM-agnostic interface for converting archaic → modern English. Prompt includes rubric format heuristics (hierarchy parsing, abbreviations like agg./amel., "of" suffix convention)
- **Vector storage**: Qdrant (local persistent) with sentence-transformers embeddings (`all-MiniLM-L6-v2`)
- **Frontend**: Streamlit app (`frontend/app.py`) with direct embedder integration (no separate API needed)
- **API**: FastAPI `/search` endpoint (optional, for programmatic access)

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run extraction script
python scripts/extract_rubrics.py

# Run translation pipeline (parallel by default, ~10x faster)
python scripts/translate_rubrics.py 100
python scripts/translate_rubrics.py 100 -c 20  # custom concurrency
python scripts/translate_rubrics.py 100 --sync  # sequential mode

# Embed translations into vector database
python scripts/embed_rubrics.py
python scripts/embed_rubrics.py --force  # re-embed all

# Start Streamlit frontend
streamlit run frontend/app.py

# Start API server (optional)
uvicorn src.api:app --reload

# Run tests
pytest tests/

# Generate test sentences for semantic search evaluation
python scripts/generate_test_sentences.py

# Evaluate semantic search quality
python scripts/evaluate_search.py --excel ../tests/test_sentences.xlsx

# Compare embedding strategies (translation vs original paths)
python scripts/compare_embeddings.py
```

## Data Files

- `data/oorep.sql.gz` - Source PostgreSQL dump from OOREP
- `data/rubrics.xlsx` - All chapters extracted (reference)
- `data/mind_rubrics.xlsx` - Mind chapter with columns: id, path, chapter, remedy_count, translation
- `tests/test_sentences.xlsx` - Test sentences for semantic search validation (120 rubrics × 10 sentences each)

Excel format chosen for easier manual inspection and smaller file size.

## Deployment

- **Live app**: https://rubricfinder-cpze8qjbitcdhswgawhmpa.streamlit.app/
- **Repository**: https://github.com/alextournier/RubricFinder
- **Hosted on**: Streamlit Community Cloud
- `qdrant_db/` is committed to Git (small, ~500KB) for deployment
- Pin `altair>=5.0.0,<6.0.0` in requirements.txt for Python 3.13 compatibility
- **Replit not viable**: sentence-transformers + PyTorch exceed 8GB image limit

## Key Design Decisions

- Search results show rubrics with remedy count (number of associated remedies)
- Embed the **translation** (not original) for better semantic matching — validated by A/B test showing 39% MRR improvement (0.55 vs 0.40) over embedding original paths
- **Embeddings DB size**: Currently ~500KB for ~5,900 Mind rubrics. Full repertory (~74,600 rubrics) estimated ~130-150MB with MiniLM-384d — well under Streamlit's 1GB repo limit
- LLM interface is pluggable (Anthropic or OpenAI)
- Excel (.xlsx) for data files — easier to inspect, single file per chapter
- 10 test sentences per rubric (short paraphrases) for validating semantic search — stored in `tests/test_sentences.xlsx`
- Test sentences should be SHORT (8-10 words max) and semantically close to the translation for best embedding match
- Current evaluation metrics (120 rubrics, 1200 queries): Hit@1: 44%, Hit@5: 71%, Hit@10: 79%, MRR: 0.55
- Qdrant (local persistent storage in `qdrant_db/`)
- Switched from ChromaDB to Qdrant due to Python 3.14 compatibility (onnxruntime unavailable)

See `FutureDevs.md` for planned improvements and ideas.

## Mathpix API Usage

*(To be documented when implemented)*

## Documentation Maintenance

When making changes that affect project structure, data formats, or design decisions:
- Update `CLAUDE.md` (this file) for architectural changes
- Update `.claude/agents/rubricfinder-manager.md` status table when components are completed
- Keep docs in sync automatically — don't wait for user to ask
