# Homeopathic Rubric Semantic Search - Implementation Plan

## Overview
Build a webapp that enables natural language search for homeopathic rubrics by:
1. Extracting rubrics from OOREP's PostgreSQL dump
2. Translating archaic rubric language to modern plain English
3. Embedding translations and storing in ChromaDB
4. Providing semantic search via web interface

## Data Source
- **OOREP PostgreSQL dump** (`oorep.sql.gz`) from [github.com/nondeterministic/oorep](https://github.com/nondeterministic/oorep)
- Start with **Mind chapter only** (~200 rubrics) for initial testing

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌───────────┐
│  OOREP SQL dump │────▶│ Extract Mind │────▶│ rubrics.json
│  (oorep.sql.gz) │     │   chapter    │     │           │
└─────────────────┘     └──────────────┘     └─────┬─────┘
                                                   │
                                                   ▼
                                          ┌───────────────┐
                                          │ LLM translate │
                                          │ to modern     │
                                          │ language      │
                                          └───────┬───────┘
                                                  │
                                                  ▼
                                          ┌───────────────┐
                                          │ Embed + store │
                                          │ in ChromaDB   │
                                          └───────┬───────┘
                                                  │
                                                  ▼
                                          ┌───────────────┐
                                          │ Flask/FastAPI │
                                          │ search API    │
                                          └───────┬───────┘
                                                  │
                                                  ▼
                                          ┌───────────────┐
                                          │ Web frontend  │
                                          │ (Replit)      │
                                          └───────────────┘
```

## Implementation Steps

### Phase 1: Data Extraction
1. Download `oorep.sql.gz` from OOREP GitHub releases
2. Parse SQL to extract `rubric` table entries
3. Filter to Mind chapter only (first chapter in Kent)
4. Output: `data/mind_rubrics.json` with structure:
   ```json
   {
     "rubrics": [
       {"id": 1, "path": "Mind > Absent-minded", "text": "ABSENT-MINDED", "remedies": [...]}
     ]
   }
   ```

### Phase 2: Translation Pipeline
1. Create translation script (LLM-agnostic interface)
2. For each rubric, prompt LLM:
   - Input: Original rubric text + full path
   - Output: Plain modern English description
3. Example translation:
   - Original: "ANGUISH, driving from place to place"
   - Modern: "Intense emotional distress causing restless movement, unable to stay still"
4. Store translations alongside originals
5. **Cache/save translations** to avoid re-running expensive LLM calls

### Phase 3: Embedding & Storage
1. Use sentence-transformers (`all-MiniLM-L6-v2` or similar) for embeddings
2. Create ChromaDB collection
3. Store: original rubric, translation, path, remedy list
4. Embed the **translation** (modern language) for better search matching

### Phase 4: Search API
1. FastAPI backend with `/search` endpoint
2. Accept natural language symptom description
3. Embed query, search ChromaDB, return top-k matches
4. Include both original rubric and translation in results

### Phase 5: Web Frontend
1. Simple HTML/JS or Streamlit interface
2. Text input for symptoms
3. Display matching rubrics with:
   - Original rubric path
   - Modern translation
   - Relevance score

### Phase 6: Testing
1. Unit tests for SQL parsing
2. Integration tests for search quality
3. Manual evaluation: test known rubrics against expected symptoms

## File Structure
```
homeo-rubric-search/
├── data/
│   ├── oorep.sql.gz          # Downloaded
│   ├── mind_rubrics.json     # Extracted
│   └── mind_translated.json  # With translations
├── scripts/
│   ├── extract_rubrics.py    # SQL parsing
│   └── translate_rubrics.py  # LLM translation
├── src/
│   ├── embedder.py           # Embedding + ChromaDB
│   ├── search.py             # Search logic
│   └── api.py                # FastAPI endpoints
├── tests/
│   ├── test_extraction.py
│   └── test_search.py
├── frontend/                 # For Replit deployment
│   └── app.py                # Streamlit or Flask
├── requirements.txt
└── README.md
```

## Dependencies
- `chromadb` - Vector database
- `sentence-transformers` - Embeddings
- `fastapi` / `flask` - API
- `streamlit` (optional) - Quick frontend
- `anthropic` or `openai` - LLM translation (configurable)

## Decisions Made
- **Replit scope**: Full stack (API + ChromaDB + frontend all on Replit)
- **Remedy display**: Rubrics only - no remedies in search results (keep simple)
- **LLM for translation**: Pluggable interface, decide during implementation

## Next Steps After Planning
1. Create project directory
2. Download and inspect OOREP SQL dump structure
3. Write extraction script for Mind chapter
4. Test with 10 rubrics before scaling
