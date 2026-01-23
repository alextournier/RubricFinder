"""FastAPI application for RubricFinder semantic search."""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .embedder import RubricEmbedder
from .models import SearchQuery, SearchResponse, RubricResult


# Global embedder instance (lazy initialized)
_embedder: Optional[RubricEmbedder] = None


def get_embedder() -> RubricEmbedder:
    """Get or create the embedder instance."""
    global _embedder
    if _embedder is None:
        _embedder = RubricEmbedder()
    return _embedder


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize embedder on startup."""
    # Pre-load embedder on startup for faster first request
    get_embedder()
    yield


app = FastAPI(
    title="RubricFinder API",
    description="Semantic search for homeopathic rubrics",
    version="0.1.0",
    lifespan=lifespan
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def health_check():
    """Health check endpoint returning collection status."""
    embedder = get_embedder()
    count = embedder.count()
    return {
        "status": "ok",
        "collection_size": count,
        "model": embedder.MODEL_NAME
    }


@app.post("/search", response_model=SearchResponse)
async def search_post(query: SearchQuery):
    """Search rubrics via POST with JSON body."""
    return _perform_search(query.query, query.top_k)


@app.get("/search", response_model=SearchResponse)
async def search_get(
    query: str = Query(..., description="Search query text"),
    top_k: int = Query(default=10, ge=1, le=100, description="Number of results")
):
    """Search rubrics via GET with query parameters."""
    return _perform_search(query, top_k)


def _perform_search(query: str, top_k: int) -> SearchResponse:
    """Execute search and return response."""
    embedder = get_embedder()

    if embedder.count() == 0:
        raise HTTPException(
            status_code=503,
            detail="No rubrics in collection. Run embed_rubrics.py first."
        )

    results = embedder.search(query, top_k)

    return SearchResponse(
        query=query,
        results=[RubricResult(**r) for r in results],
        total_in_collection=embedder.count()
    )
