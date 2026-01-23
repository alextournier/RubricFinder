"""Qdrant wrapper for rubric embeddings."""

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


class RubricEmbedder:
    """Manages rubric embeddings in Qdrant."""

    COLLECTION_NAME = "rubrics"
    MODEL_NAME = "all-MiniLM-L6-v2"  # 384 dims, ~80MB, good quality/size balance
    VECTOR_SIZE = 384
    BATCH_SIZE = 500

    def __init__(self, persist_dir: str | Path = "qdrant_db"):
        """Initialize Qdrant client with persistent storage."""
        self.persist_dir = Path(persist_dir)
        self.client = QdrantClient(path=str(self.persist_dir))

        # Load sentence-transformers model
        self.model = SentenceTransformer(self.MODEL_NAME)

        # Create collection if it doesn't exist
        collections = self.client.get_collections().collections
        if not any(c.name == self.COLLECTION_NAME for c in collections):
            self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=self.VECTOR_SIZE,
                    distance=Distance.COSINE
                )
            )

    def add_rubrics(self, rubrics: list[RubricData], skip_existing: bool = True) -> int:
        """
        Add rubrics to the collection.

        Args:
            rubrics: List of rubric data dicts with id, path, translation, chapter
            skip_existing: If True, skip rubrics already in collection

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

            # Generate embeddings
            texts = [r["translation"] for r in batch]
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
                        "chapter": r["chapter"]
                    }
                )
                for r, embedding in zip(batch, embeddings)
            ]

            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
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
            collection_name=self.COLLECTION_NAME,
            query=query_embedding,
            limit=min(top_k, max(1, self.count()))
        )

        return [
            {
                "rubric_id": hit.payload["rubric_id"],
                "path": hit.payload["path"],
                "translation": hit.payload["translation"],
                "chapter": hit.payload["chapter"],
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
                collection_name=self.COLLECTION_NAME,
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
        info = self.client.get_collection(self.COLLECTION_NAME)
        return info.points_count

    def clear(self) -> None:
        """Delete all rubrics from collection."""
        self.client.delete_collection(self.COLLECTION_NAME)
        self.client.create_collection(
            collection_name=self.COLLECTION_NAME,
            vectors_config=VectorParams(
                size=self.VECTOR_SIZE,
                distance=Distance.COSINE
            )
        )
