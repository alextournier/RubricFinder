"""Streamlit frontend for RubricFinder semantic search."""

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
    """Load embedder once, cached across reruns."""
    return RubricEmbedder(persist_dir=PROJECT_ROOT / "qdrant_db")


st.set_page_config(page_title="RubricFinder", page_icon="🔍", layout="wide")
st.title("RubricFinder")

embedder = get_embedder()
rubric_count = embedder.count()

st.sidebar.markdown(f"**Collection:** {rubric_count:,} rubrics")

if rubric_count == 0:
    st.warning("No rubrics in database. Run `python scripts/embed_rubrics.py` first.")
    st.stop()

query = st.text_input("Describe the symptom in modern language...", placeholder="e.g., fear of being alone")

if query:
    results = embedder.search(query, top_k=10)

    if not results:
        st.info("No results found.")
    else:
        import pandas as pd

        df = pd.DataFrame([
            {
                "Score": f"{r['score']:.3f}",
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
