"""Pydantic models for RubricFinder API."""

from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """Search request body."""
    query: str = Field(..., description="Search query text")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results to return")


class RubricResult(BaseModel):
    """Single rubric search result."""
    rubric_id: str
    path: str
    translation: str
    chapter: str
    score: float = Field(..., description="Similarity score (higher is better)")


class SearchResponse(BaseModel):
    """Search response containing results."""
    query: str
    results: list[RubricResult]
    total_in_collection: int
