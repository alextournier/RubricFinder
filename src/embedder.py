"""Qdrant wrapper for rubric embeddings."""

import os
from pathlib import Path
from typing import TypedDict

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer


class RubricData(TypedDict):
    """Rubric data for embedding."""
    id: str
    path: str
    translation: str
    chapter: str
    remedy_count: int


class RubricEmbedder:
    """Manages rubric embeddings in Qdrant (local or cloud)."""

    DEFAULT_COLLECTION = "rubrics"
    MODEL_NAME = "all-MiniLM-L6-v2"  # 384 dims, ~80MB, good quality/size balance
    VECTOR_SIZE = 384
    BATCH_SIZE = 500

    def __init__(
        self,
        persist_dir: str | Path = "qdrant_db",
        collection_name: str | None = None,
        url: str | None = None,
        api_key: str | None = None,
    ):
        """
        Initialize Qdrant client.

        For cloud: provide url and api_key, or set QDRANT_URL and QDRANT_API_KEY env vars.
        For local: omit url/api_key, uses persist_dir for storage.

        Args:
            persist_dir: Directory for local Qdrant storage (ignored if using cloud)
            collection_name: Name of collection to use (default: "rubrics")
            url: Qdrant Cloud URL (or set QDRANT_URL env var)
            api_key: Qdrant Cloud API key (or set QDRANT_API_KEY env var)
        """
        self.collection_name = collection_name or self.DEFAULT_COLLECTION

        # Check for cloud config (explicit params or env vars)
        cloud_url = url or os.environ.get("QDRANT_URL")
        cloud_key = api_key or os.environ.get("QDRANT_API_KEY")

        if cloud_url and cloud_key:
            # Cloud mode
            self.client = QdrantClient(url=cloud_url, api_key=cloud_key)
            self.mode = "cloud"
        else:
            # Local mode
            self.persist_dir = Path(persist_dir)
            self.client = QdrantClient(path=str(self.persist_dir))
            self.mode = "local"

        # Load sentence-transformers model
        self.model = SentenceTransformer(self.MODEL_NAME)

        # Create collection if it doesn't exist
        self._ensure_collection()

    def _ensure_collection(self):
        """Create collection if it doesn't exist."""
        collections = self.client.get_collections().collections
        if not any(c.name == self.collection_name for c in collections):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.VECTOR_SIZE,
                    distance=Distance.COSINE
                )
            )

    def add_rubrics(
        self,
        rubrics: list[RubricData],
        skip_existing: bool = True,
        text_field: str = "translation"
    ) -> int:
        """
        Add rubrics to the collection.

        Args:
            rubrics: List of rubric data dicts with id, path, translation, chapter
            skip_existing: If True, skip rubrics already in collection
            text_field: Which field to embed ("translation" or "path")

        Returns:
            Number of rubrics added
        """
        if skip_existing:
            existing_ids = set(self.get_existing_ids())
            rubrics = [r for r in rubrics if r["id"] not in existing_ids]

        if not rubrics:
            return 0

        added = 0
        for i in range(0, len(rubrics), self.BATCH_SIZE):
            batch = rubrics[i:i + self.BATCH_SIZE]

            # Generate embeddings from specified field
            texts = [r[text_field] for r in batch]
            embeddings = self.model.encode(texts, show_progress_bar=len(batch) > 100)

            # Create points
            points = [
                PointStruct(
                    id=hash(r["id"]) & 0x7FFFFFFFFFFFFFFF,  # Convert to positive int
                    vector=embedding.tolist(),
                    payload={
                        "rubric_id": r["id"],
                        "path": r["path"],
                        "translation": r["translation"],
                        "chapter": r["chapter"],
                        "remedy_count": r.get("remedy_count", 0)
                    }
                )
                for r, embedding in zip(batch, embeddings)
            ]

            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            added += len(batch)

        return added

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """
        Search for rubrics matching the query.

        Args:
            query: Search query text
            top_k: Number of results to return

        Returns:
            List of result dicts with rubric_id, path, translation, chapter, score
        """
        query_embedding = self.model.encode(query).tolist()

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=min(top_k, max(1, self.count()))
        )

        return [
            {
                "rubric_id": hit.payload["rubric_id"],
                "path": hit.payload["path"],
                "translation": hit.payload["translation"],
                "chapter": hit.payload["chapter"],
                "remedy_count": hit.payload.get("remedy_count", 0),
                "score": round(hit.score, 4)
            }
            for hit in results.points
        ]

    def get_existing_ids(self) -> list[str]:
        """Get all rubric IDs currently in the collection."""
        count = self.count()
        if count == 0:
            return []

        # Scroll through all points to get IDs
        ids = []
        offset = None
        while True:
            result, offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000,
                offset=offset,
                with_payload=["rubric_id"]
            )
            ids.extend(point.payload["rubric_id"] for point in result)
            if offset is None:
                break

        return ids

    def count(self) -> int:
        """Return number of rubrics in collection."""
        info = self.client.get_collection(self.collection_name)
        return info.points_count

    def clear(self) -> None:
        """Delete all rubrics from collection."""
        self.client.delete_collection(self.collection_name)
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.VECTOR_SIZE,
                distance=Distance.COSINE
            )
        )
