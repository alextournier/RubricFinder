"""Streamlit frontend for RubricFinder semantic search."""

import time

import streamlit as st
import sys
from pathlib import Path

# Project root (parent of frontend/)
PROJECT_ROOT = Path(__file__).parent.parent

# Add project root to path for imports
sys.path.insert(0, str(PROJECT_ROOT))

from src.embedder import RubricEmbedder


@st.cache_resource
def get_embedder():
    """Load embedder once, cached across reruns.

    Uses Qdrant Cloud if QDRANT_URL and QDRANT_API_KEY are in secrets,
    otherwise falls back to local storage.
    """
    # Check for Qdrant Cloud credentials in Streamlit secrets
    qdrant_url = st.secrets.get("QDRANT_URL") if hasattr(st, "secrets") else None
    qdrant_key = st.secrets.get("QDRANT_API_KEY") if hasattr(st, "secrets") else None

    if qdrant_url and qdrant_key:
        return RubricEmbedder(url=qdrant_url, api_key=qdrant_key)
    else:
        return RubricEmbedder(persist_dir=PROJECT_ROOT / "qdrant_db")


st.set_page_config(page_title="RubricFinder", page_icon="🔍", layout="wide")
st.title("RubricFinder")

embedder = get_embedder()
rubric_count = embedder.count()

st.sidebar.markdown(f"**Collection:** {rubric_count:,} rubrics")
st.sidebar.markdown(f"**Mode:** {embedder.mode}")

if rubric_count == 0:
    st.warning("No rubrics in database. Run `python scripts/embed_rubrics.py` first.")
    st.stop()

query = st.text_input("Describe the symptom in modern language...", placeholder="e.g., fear of being alone")

if query:
    start_time = time.time()
    results = embedder.search(query, top_k=10)
    elapsed = time.time() - start_time

    if not results:
        st.info("No results found.")
    else:
        st.caption(f"Found {len(results)} results in {elapsed:.3f}s")
        import pandas as pd

        df = pd.DataFrame([
            {
                "Score": f"{r['score']:.3f}",
                "Remedies": r.get('remedy_count', 0),
                "Chapter": r['chapter'],
                "Path": r['path'],
                "Translation": r['translation'],
            }
            for r in results
        ])

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )
