#!/usr/bin/env python3
"""Evaluate semantic search quality using test sentences."""

import argparse
import sys
from pathlib import Path

import pandas as pd
from tqdm import tqdm

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.embedder import RubricEmbedder

DATA_DIR = Path(__file__).parent.parent / "data"


def evaluate_search(excel_path: Path, verbose: bool = False, output_path: Path | None = None):
    """
    Evaluate search quality using test sentences as queries.

    For each rubric with translation, query each test sentence and measure
    how well the search retrieves the correct original rubric.
    """
    # Load data
    df = pd.read_excel(excel_path)
    if "translation" in df.columns:
        df = df[df["translation"].notna()].copy()

    print(f"Loaded {len(df)} rubrics")

    # Initialize embedder
    print("Initializing embedder...")
    embedder = RubricEmbedder()

    embedded_count = embedder.count()
    print(f"Embeddings in database: {embedded_count}")

    # Find test columns
    test_cols = [c for c in df.columns if c.startswith("test_")]
    print(f"Test columns found: {len(test_cols)}")

    # Evaluation results
    results = []
    total_queries = 0
    hits_at_1 = 0
    hits_at_3 = 0
    hits_at_5 = 0
    hits_at_10 = 0
    reciprocal_ranks = []
    scores_when_found = []

    # Evaluate each rubric
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Evaluating rubrics"):
        rubric_id = str(row["id"])
        rubric_path = row["path"]

        rubric_results = {
            "id": rubric_id,
            "path": rubric_path,
        }
        if "translation" in row:
            rubric_results["translation"] = row["translation"]

        for test_col in test_cols:
            test_sentence = row.get(test_col)
            if pd.isna(test_sentence) or not str(test_sentence).strip():
                continue

            test_sentence = str(test_sentence).strip()
            total_queries += 1

            # Search
            search_results = embedder.search(test_sentence, top_k=10)

            # Find rank of correct rubric
            rank = None
            score = None
            for i, result in enumerate(search_results):
                if result["rubric_id"] == rubric_id:
                    rank = i + 1  # 1-indexed
                    score = result["score"]
                    break

            # Record metrics
            if rank is not None:
                if rank == 1:
                    hits_at_1 += 1
                if rank <= 3:
                    hits_at_3 += 1
                if rank <= 5:
                    hits_at_5 += 1
                if rank <= 10:
                    hits_at_10 += 1
                reciprocal_ranks.append(1 / rank)
                scores_when_found.append(score)
            else:
                reciprocal_ranks.append(0)

            rubric_results[f"{test_col}_rank"] = rank if rank else ">10"
            rubric_results[f"{test_col}_score"] = score if score else None

            if verbose:
                status = f"rank {rank}" if rank else "NOT FOUND"
                print(f"  {test_col}: {status} (query: {test_sentence[:50]}...)")

        results.append(rubric_results)

    # Calculate metrics
    hit_at_1_pct = (hits_at_1 / total_queries * 100) if total_queries else 0
    hit_at_3_pct = (hits_at_3 / total_queries * 100) if total_queries else 0
    hit_at_5_pct = (hits_at_5 / total_queries * 100) if total_queries else 0
    hit_at_10_pct = (hits_at_10 / total_queries * 100) if total_queries else 0
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0
    avg_score = sum(scores_when_found) / len(scores_when_found) if scores_when_found else 0

    # Print results
    print("\n" + "=" * 40)
    print("SEARCH EVALUATION RESULTS")
    print("=" * 40)
    print(f"Test queries: {total_queries}")
    print(f"Rubrics tested: {len(df)}")
    print()
    print(f"Hit@1:  {hit_at_1_pct:5.1f}%")
    print(f"Hit@3:  {hit_at_3_pct:5.1f}%")
    print(f"Hit@5:  {hit_at_5_pct:5.1f}%")
    print(f"Hit@10: {hit_at_10_pct:5.1f}%")
    print(f"MRR:    {mrr:.3f}")
    print(f"Avg score when found: {avg_score:.3f}")

    # Save results to Excel with two sheets
    if output_path:
        # Summary sheet
        summary_df = pd.DataFrame([
            {"Metric": "Test queries", "Value": total_queries},
            {"Metric": "Rubrics tested", "Value": len(df)},
            {"Metric": "Hit@1", "Value": f"{hit_at_1_pct:.1f}%"},
            {"Metric": "Hit@3", "Value": f"{hit_at_3_pct:.1f}%"},
            {"Metric": "Hit@5", "Value": f"{hit_at_5_pct:.1f}%"},
            {"Metric": "Hit@10", "Value": f"{hit_at_10_pct:.1f}%"},
            {"Metric": "MRR", "Value": f"{mrr:.3f}"},
            {"Metric": "Avg score when found", "Value": f"{avg_score:.3f}"},
        ])

        # Details sheet
        results_df = pd.DataFrame(results)

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            summary_df.to_excel(writer, sheet_name="Summary", index=False)
            results_df.to_excel(writer, sheet_name="Details", index=False)

        print(f"\nResults saved to: {output_path}")

    return {
        "total_queries": total_queries,
        "rubrics_tested": len(df),
        "hit_at_1": hit_at_1_pct,
        "hit_at_3": hit_at_3_pct,
        "hit_at_5": hit_at_5_pct,
        "hit_at_10": hit_at_10_pct,
        "mrr": mrr,
        "avg_score": avg_score,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate semantic search quality")
    parser.add_argument("--excel", default="mind_rubrics.xlsx", help="Excel file name in data/ directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print each query result")
    parser.add_argument("--output", "-o", help="Save detailed results to Excel file")
    args = parser.parse_args()

    excel_path = DATA_DIR / args.excel
    if not excel_path.exists():
        print(f"Error: {excel_path} not found")
        return 1

    output_path = None
    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = DATA_DIR / output_path

    evaluate_search(excel_path, verbose=args.verbose, output_path=output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
