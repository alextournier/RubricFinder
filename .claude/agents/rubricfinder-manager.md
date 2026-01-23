---
name: rubricfinder-manager
description: "Reference doc for RubricFinder project state, architecture, and build order. Use when you need project context or to check what's next."
model: haiku
color: blue
---

# RubricFinder Project Reference

## Architecture

```
OOREP SQL dump → Extract rubrics → LLM translation → Qdrant embeddings → FastAPI → Web frontend
```

## Current Status

**Phase: Core pipeline complete, frontend needed**

| Component | Status | Notes |
|-----------|--------|-------|
| requirements.txt | ✅ | All deps including tqdm for progress bars |
| data/oorep.sql.gz | ✅ | 6.2 MB source data |
| scripts/extract_rubrics.py | ✅ | Outputs Excel (all chapters) |
| data/rubrics.xlsx | ✅ | 1.9 MB, all 41 chapters |
| data/mind_rubrics.xlsx | ✅ | 5930 rubrics (translation in progress) |
| scripts/translate_rubrics.py | ✅ | With tqdm progress bar |
| scripts/embed_rubrics.py | ✅ | Loads Excel → Qdrant |
| scripts/evaluate_search.py | ✅ | Test search quality |
| src/embedder.py | ✅ | Qdrant integration (all-MiniLM-L6-v2) |
| src/api.py | ✅ | FastAPI GET/POST /search |
| src/models.py | ✅ | Pydantic models |
| frontend/ | ❌ | Final phase |

**Next**: Complete translations → Build frontend (Streamlit or HTML/JS)

**Last updated**: 2026-01-23

## Build Order

1. ✅ `requirements.txt` (qdrant-client, sentence-transformers, fastapi, uvicorn, anthropic, openpyxl, tqdm)
2. ✅ `data/oorep.sql.gz` from github.com/nondeterministic/oorep
3. ✅ `scripts/extract_rubrics.py` → `data/rubrics.xlsx`
4. ✅ Filter Mind chapter → `data/mind_rubrics.xlsx`
5. 🔄 `scripts/translate_rubrics.py` (in progress)
6. ✅ `src/embedder.py` (Qdrant with sentence-transformers)
7. ✅ `src/api.py` (FastAPI /search GET and POST)
8. ❌ `frontend/` (Streamlit or HTML/JS)

## Data Schema

`mind_rubrics.xlsx` — single table, columns added progressively:

| Column | Description |
|--------|-------------|
| id | Rubric ID from OOREP |
| path | Hierarchical rubric path |
| text | Original archaic rubric text |
| translation | Modern English translation (LLM) |
| test_1..test_10 | 10 paraphrase sentences for search validation |

## Key Commands

```bash
pip install -r requirements.txt
python scripts/extract_rubrics.py
python scripts/translate_rubrics.py 100   # translate N rubrics
python scripts/embed_rubrics.py           # embed to Qdrant
python scripts/embed_rubrics.py --force   # re-embed all
python scripts/evaluate_search.py         # test search quality
uvicorn src.api:app --reload              # start API server
pytest tests/
```

## Environment Variables

```bash
export ANTHROPIC_API_KEY="sk-ant-..."  # For translation
export OPENAI_API_KEY="sk-..."         # Alternative
```

## Design Constraints

- Search returns rubrics only, no remedies
- Embed translations, not original archaic text
- Excel format for data files (easier to inspect)
- LLM interface pluggable (Anthropic or OpenAI)
- Translation script skips already-filled rows (incremental)
- Qdrant for vector storage (Python 3.14 compatible, unlike ChromaDB/onnxruntime)
- Persistent storage in `qdrant_db/` directory

## Cost Note

Translation is expensive. Test on 10-20 rubrics first. ~300 tokens per rubric (1 translation + 10 test sentences).
