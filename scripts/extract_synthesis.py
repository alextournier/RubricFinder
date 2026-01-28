#!/usr/bin/env python3
"""Extract rubrics from Synthesis repertory text file."""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"


def extract_rubrics(txt_path: Path) -> pd.DataFrame:
    """Parse Synthesis text file into DataFrame.

    Format: One rubric per line, path uses ' - ' as separator.
    Example: MIND - ABSENTMINDED - morning
    """
    rubrics = []

    with open(txt_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            path = line.strip()
            if not path:
                continue

            # Extract chapter (first element before ' - ')
            parts = path.split(" - ")
            chapter = parts[0] if parts else ""

            rubrics.append({
                "id": i,
                "path": path,
                "chapter": chapter,
            })

    df = pd.DataFrame(rubrics)

    # Filter to MIND chapter only (exclude cross-references)
    mind_only = df[df["chapter"] == "MIND"].copy()
    if len(mind_only) < len(df):
        excluded = len(df) - len(mind_only)
        print(f"Filtered out {excluded} non-MIND cross-references")
    mind_only["id"] = range(1, len(mind_only) + 1)  # Re-index

    return mind_only


def main():
    txt_path = DATA_DIR / "MIND_only_book188_Synthesys.txt"

    if not txt_path.exists():
        print(f"Error: {txt_path} not found.")
        return

    print(f"Parsing {txt_path}...")
    df = extract_rubrics(txt_path)

    if df.empty:
        print("Error: No rubrics found!")
        return

    # Summary
    print(f"\n{'='*60}")
    print(f"EXTRACTION SUMMARY")
    print(f"{'='*60}")
    print(f"Total rubrics: {len(df):,}")
    print(f"\nRubrics by chapter:")
    print(df["chapter"].value_counts().to_string())

    # Save to Excel
    excel_path = DATA_DIR / "synthesis_mind_rubrics.xlsx"
    df.to_excel(excel_path, index=False)
    print(f"\nSaved to {excel_path}")

    # Show samples
    print(f"\n{'='*60}")
    print("SAMPLE RUBRICS (first 20)")
    print(f"{'='*60}")
    pd.set_option('display.max_colwidth', 100)
    pd.set_option('display.width', 200)
    print(df.head(20).to_string(index=False))

    # Show some deeper hierarchy examples
    print(f"\n{'='*60}")
    print("DEEP HIERARCHY EXAMPLES")
    print(f"{'='*60}")
    deep = df[df["path"].str.count(" - ") >= 4].head(20)
    print(deep.to_string(index=False))


if __name__ == "__main__":
    main()
