#!/usr/bin/env python3
"""Embed translated rubrics into ChromaDB."""

import argparse
import sys
from pathlib import Path

import pandas as pd

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.embedder import RubricEmbedder, RubricData

DATA_DIR = Path(__file__).parent.parent / "data"


def load_rubrics_with_translations(excel_path: Path) -> list[RubricData]:
    """Load rubrics that have translations from Excel file."""
    df = pd.read_excel(excel_path)

    # Filter to rows with translations
    df = df[df["translation"].notna()].copy()

    rubrics = []
    for _, row in df.iterrows():
        rubrics.append({
            "id": str(row["id"]),
            "path": str(row["path"]),
            "translation": str(row["translation"]),
            "chapter": str(row["chapter"]),
            "remedy_count": int(row.get("remedy_count", 0)) if pd.notna(row.get("remedy_count")) else 0
        })

    return rubrics


def main():
    parser = argparse.ArgumentParser(description="Embed translated rubrics into ChromaDB")
    parser.add_argument("--force", action="store_true", help="Clear existing embeddings and re-embed all")
    parser.add_argument("--excel", default="mind_rubrics.xlsx", help="Excel file name in data/ directory")
    args = parser.parse_args()

    excel_path = DATA_DIR / args.excel
    if not excel_path.exists():
        print(f"Error: {excel_path} not found")
        return 1

    print(f"Loading rubrics from {excel_path}...")
    rubrics = load_rubrics_with_translations(excel_path)
    print(f"Found {len(rubrics)} rubrics with translations")

    if not rubrics:
        print("No rubrics with translations found. Run translate_rubrics.py first.")
        return 1

    print("Initializing embedder (loading model)...")
    embedder = RubricEmbedder()

    if args.force:
        print("Clearing existing embeddings...")
        embedder.clear()

    existing_count = embedder.count()
    print(f"Existing embeddings: {existing_count}")

    print("Adding rubrics to vector database...")
    added = embedder.add_rubrics(rubrics, skip_existing=not args.force)

    final_count = embedder.count()
    print(f"\nResults:")
    print(f"  Added: {added} rubrics")
    print(f"  Skipped: {len(rubrics) - added} (already embedded)")
    print(f"  Total in collection: {final_count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
