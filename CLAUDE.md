# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RubricFinder is a semantic search webapp for homeopathic rubrics. It extracts rubrics from the OOREP PostgreSQL dump, translates archaic rubric language to modern English using LLMs, embeds translations in ChromaDB, and provides search via a web interface.

## Architecture

```
OOREP SQL dump → Extract rubrics → LLM translation → Embed in ChromaDB → FastAPI → Web frontend
```

Key components:
- **Data extraction**: Parse `oorep.sql.gz` to extract rubrics (starting with Mind chapter)
- **Translation pipeline**: LLM-agnostic interface for converting archaic → modern English
- **Vector storage**: ChromaDB with sentence-transformers embeddings on translated text
- **API**: FastAPI `/search` endpoint
- **Frontend**: Streamlit or simple HTML/JS

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run extraction script
python scripts/extract_rubrics.py

# Run translation pipeline
python scripts/translate_rubrics.py

# Start API server
uvicorn src.api:app --reload

# Run tests
pytest tests/
```

## Data Files

- `data/oorep.sql.gz` - Source PostgreSQL dump from OOREP
- `data/mind_rubrics.json` - Extracted rubrics
- `data/mind_translated.json` - Rubrics with modern English translations (cached to avoid re-running LLM)

## Key Design Decisions

- Search results show rubrics only, no remedies (keep simple)
- Embed the **translation** (not original) for better semantic matching
- LLM interface is pluggable (Anthropic or OpenAI)
- ChromaDB, API, and frontend all run on Replit

## Mathpix API Usage

*(To be documented when implemented)*
