# RubricFinder

## Overview

RubricFinder is a semantic search web app for homeopathic rubrics. It extracts rubrics from the OOREP PostgreSQL dump, translates archaic rubric language to modern English using LLMs, embeds translations in Qdrant, and provides search via a Streamlit web interface.

## Architecture

```
OOREP SQL dump → Extract rubrics → LLM translation → Embed in Qdrant → Streamlit frontend
```

### Key Components
- **Data extraction**: Parse `oorep.sql.gz` to extract rubrics (starting with Mind chapter)
- **Translation pipeline**: LLM-agnostic interface for converting archaic → modern English
- **Vector storage**: Qdrant (local persistent in `qdrant_db/`) with sentence-transformers embeddings (`all-MiniLM-L6-v2`)
- **Frontend**: Streamlit app (`frontend/app.py`) with direct embedder integration
- **API**: FastAPI `/search` endpoint (optional, for programmatic access)

## Project Structure

```
├── scripts/
│   ├── download_dump.py      # Download OOREP SQL dump
│   ├── extract_rubrics.py    # Extract rubrics from SQL
│   ├── translate_rubrics.py  # Translate via LLM
│   ├── embed_rubrics.py      # Embed into Qdrant
│   └── evaluate_search.py    # Evaluate search quality
├── src/                      # Core modules (embedder, API)
├── frontend/
│   └── app.py                # Streamlit search interface
├── tests/                    # Test suite
├── data/                     # Data files (rubrics.xlsx, etc.)
└── doc/                      # Documentation
```

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

# Start Streamlit frontend (port 5000)
streamlit run frontend/app.py --server.port 5000

# Start API server (optional)
uvicorn src.api:app --reload

# Run tests
pytest tests/
```

## Data Source

- **Repertorium Publicum**: First free open-source homeopathic repertory
- **Author**: Vladimir Polony (Slovakia)
- **OOREP dump**: 74,667 English rubrics across 41 chapters
- **License**: GPL v3

## Recent Changes

- Initial project setup from git

## User Preferences

- (To be documented as preferences are expressed)
