# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RubricFinder is a semantic search webapp for homeopathic rubrics. It extracts rubrics from the OOREP PostgreSQL dump, translates archaic rubric language to modern English using LLMs, embeds translations in Qdrant, and provides search via a web interface.

## Architecture

```
OOREP SQL dump → Extract rubrics → LLM translation → Embed in Qdrant → Streamlit frontend
```

Key components:
- **Data extraction**: Parse `oorep.sql.gz` to extract rubrics (starting with Mind chapter)
- **Translation pipeline**: LLM-agnostic interface for converting archaic → modern English
- **Vector storage**: Qdrant (local persistent) with sentence-transformers embeddings (`all-MiniLM-L6-v2`)
- **Frontend**: Streamlit app (`frontend/app.py`) with direct embedder integration (no separate API needed)
- **API**: FastAPI `/search` endpoint (optional, for programmatic access)

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run extraction script
python scripts/extract_rubrics.py

# Run translation pipeline
python scripts/translate_rubrics.py 100

# Embed translations into vector database
python scripts/embed_rubrics.py
python scripts/embed_rubrics.py --force  # re-embed all

# Start Streamlit frontend
streamlit run frontend/app.py

# Start API server (optional)
uvicorn src.api:app --reload

# Run tests
pytest tests/
```

## Data Files

- `data/oorep.sql.gz` - Source PostgreSQL dump from OOREP
- `data/rubrics.xlsx` - All chapters extracted (reference)
- `data/mind_rubrics.xlsx` - Mind chapter with columns: id, path, text, translation, test_1..test_10

Excel format chosen for easier manual inspection and smaller file size. Translation and test sentences are added as columns to the same file (no separate translation file).

## Deployment

- **Hosted on**: Streamlit Community Cloud (https://share.streamlit.io)
- **Repository**: https://github.com/alextournier/RubricFinder
- `qdrant_db/` is committed to Git (small, ~500KB) for deployment
- Pin `altair>=5.0.0,<6.0.0` in requirements.txt for Python 3.13 compatibility

## Key Design Decisions

- Search results show rubrics only, no remedies (keep simple)
- Embed the **translation** (not original) for better semantic matching
- LLM interface is pluggable (Anthropic or OpenAI)
- Excel (.xlsx) for data files — easier to inspect, single file per chapter
- 10 test sentences per rubric (paraphrases) for validating semantic search
- Qdrant (local persistent storage in `qdrant_db/`)
- Switched from ChromaDB to Qdrant due to Python 3.14 compatibility (onnxruntime unavailable)

## Mathpix API Usage

*(To be documented when implemented)*

## Documentation Maintenance

When making changes that affect project structure, data formats, or design decisions:
- Update `CLAUDE.md` (this file) for architectural changes
- Update `.claude/agents/rubricfinder-manager.md` status table when components are completed
- Keep docs in sync automatically — don't wait for user to ask
