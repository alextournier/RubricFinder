#!/usr/bin/env python3
"""Compare search quality: original rubric paths vs LLM translations."""

import sys
from pathlib import Path

import pandas as pd
from tqdm import tqdm
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

DATA_DIR = Path(__file__).parent.parent / "data"
TESTS_DIR = Path(__file__).parent.parent / "tests"

# Model configuration
MODEL_NAME = "all-MiniLM-L6-v2"
VECTOR_SIZE = 384


def ensure_collection(client: QdrantClient, name: str) -> None:
    """Create collection if it doesn't exist."""
    collections = client.get_collections().collections
    if not any(c.name == name for c in collections):
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
        )


def embed_to_collection(
    client: QdrantClient,
    model: SentenceTransformer,
    collection_name: str,
    rubrics_df: pd.DataFrame,
    text_field: str
) -> int:
    """Embed rubrics into a collection using specified text field."""
    ensure_collection(client, collection_name)

    # Check if already populated
    count = client.get_collection(collection_name).points_count
    if count == len(rubrics_df):
        print(f"Collection '{collection_name}' already has {count} rubrics")
        return count

    # Clear and re-embed
    client.delete_collection(collection_name)
    ensure_collection(client, collection_name)

    # Prepare data
    rubrics = []
    for _, row in rubrics_df.iterrows():
        rubrics.append({
            "id": str(row["id"]),
            "path": row["path"],
            "translation": row.get("translation", row["path"]),
            "chapter": row.get("chapter", "Mind"),
            "remedy_count": int(row.get("remedy_count", 0)),
        })

    # Generate embeddings
    print(f"Embedding {len(rubrics)} rubrics using '{text_field}' field...")
    texts = [r[text_field] for r in rubrics]
    embeddings = model.encode(texts, show_progress_bar=True)

    # Create points
    points = [
        PointStruct(
            id=hash(r["id"]) & 0x7FFFFFFFFFFFFFFF,
            vector=embedding.tolist(),
            payload={
                "rubric_id": r["id"],
                "path": r["path"],
                "translation": r["translation"],
                "chapter": r["chapter"],
                "remedy_count": r["remedy_count"],
            }
        )
        for r, embedding in zip(rubrics, embeddings)
    ]

    client.upsert(collection_name=collection_name, points=points)
    print(f"Added {len(points)} rubrics to '{collection_name}'")
    return len(points)


def search_collection(
    client: QdrantClient,
    model: SentenceTransformer,
    collection_name: str,
    query: str,
    top_k: int = 10
) -> list[dict]:
    """Search a collection."""
    query_embedding = model.encode(query).tolist()
    results = client.query_points(
        collection_name=collection_name,
        query=query_embedding,
        limit=top_k
    )
    return [
        {"rubric_id": hit.payload["rubric_id"], "score": hit.score}
        for hit in results.points
    ]


def evaluate_collection(
    client: QdrantClient,
    model: SentenceTransformer,
    collection_name: str,
    test_df: pd.DataFrame,
    label: str
) -> dict:
    """Run evaluation against a specific collection."""
    test_cols = [c for c in test_df.columns if c.startswith("test_")]

    total_queries = 0
    hits_at_1 = 0
    hits_at_5 = 0
    hits_at_10 = 0
    reciprocal_ranks = []

    for _, row in tqdm(test_df.iterrows(), total=len(test_df), desc=f"Evaluating {label}"):
        rubric_id = str(row["id"])

        for test_col in test_cols:
            test_sentence = row.get(test_col)
            if pd.isna(test_sentence) or not str(test_sentence).strip():
                continue

            test_sentence = str(test_sentence).strip()
            total_queries += 1

            # Search
            search_results = search_collection(client, model, collection_name, test_sentence, top_k=10)

            # Find rank of correct rubric
            rank = None
            for i, result in enumerate(search_results):
                if result["rubric_id"] == rubric_id:
                    rank = i + 1
                    break

            if rank is not None:
                if rank == 1:
                    hits_at_1 += 1
                if rank <= 5:
                    hits_at_5 += 1
                if rank <= 10:
                    hits_at_10 += 1
                reciprocal_ranks.append(1 / rank)
            else:
                reciprocal_ranks.append(0)

    return {
        "total_queries": total_queries,
        "hit_at_1": hits_at_1 / total_queries * 100 if total_queries else 0,
        "hit_at_5": hits_at_5 / total_queries * 100 if total_queries else 0,
        "hit_at_10": hits_at_10 / total_queries * 100 if total_queries else 0,
        "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0,
    }


def main():
    # Load rubrics with translations
    rubrics_path = DATA_DIR / "mind_rubrics.xlsx"
    if not rubrics_path.exists():
        print(f"Error: {rubrics_path} not found")
        return 1

    rubrics_df = pd.read_excel(rubrics_path)
    rubrics_with_translation = rubrics_df[rubrics_df["translation"].notna()].copy()
    print(f"Loaded {len(rubrics_with_translation)} rubrics with translations")

    # Load test sentences
    test_path = TESTS_DIR / "test_sentences.xlsx"
    if not test_path.exists():
        print(f"Error: {test_path} not found")
        return 1

    test_df = pd.read_excel(test_path)
    print(f"Loaded {len(test_df)} test rubrics")

    # Initialize single Qdrant client and model
    print("\n--- Setting up Qdrant and model ---")
    client = QdrantClient(path="qdrant_db")
    model = SentenceTransformer(MODEL_NAME)

    # Check existing translation embeddings
    translation_count = client.get_collection("rubrics").points_count
    print(f"Translation embeddings: {translation_count} rubrics")

    # Create original path embeddings
    print("\n--- Creating original path embeddings ---")
    embed_to_collection(client, model, "rubrics_original", rubrics_with_translation, "path")

    # Run evaluations
    print("\n--- Running evaluations ---")
    translation_results = evaluate_collection(client, model, "rubrics", test_df, "Translation")
    original_results = evaluate_collection(client, model, "rubrics_original", test_df, "Original")

    # Print comparison
    print("\n" + "=" * 55)
    print("EMBEDDING COMPARISON RESULTS")
    print("=" * 55)
    print(f"{'Metric':<15} {'Translation':>15} {'Original':>15}")
    print("-" * 55)
    print(f"{'Hit@1:':<15} {translation_results['hit_at_1']:>14.1f}% {original_results['hit_at_1']:>14.1f}%")
    print(f"{'Hit@5:':<15} {translation_results['hit_at_5']:>14.1f}% {original_results['hit_at_5']:>14.1f}%")
    print(f"{'Hit@10:':<15} {translation_results['hit_at_10']:>14.1f}% {original_results['hit_at_10']:>14.1f}%")
    print(f"{'MRR:':<15} {translation_results['mrr']:>15.3f} {original_results['mrr']:>15.3f}")
    print("-" * 55)

    # Determine winner
    if translation_results['mrr'] > original_results['mrr'] * 1.05:
        print("Winner: Translation embeddings perform better")
    elif original_results['mrr'] > translation_results['mrr'] * 1.05:
        print("Winner: Original path embeddings perform better")
    else:
        print("Result: Performance is similar (within 5%)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
