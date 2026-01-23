#!/usr/bin/env python3
"""Extract rubrics from OOREP PostgreSQL dump into a pandas DataFrame."""

import gzip
import re
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"

# Filter to this repertory (publicum = English, kent-de = German)
REPERTORY = "publicum"


def parse_copy_block(lines: list[str], columns: list[str]) -> list[dict]:
    """Parse a COPY block into list of dicts."""
    rows = []
    for line in lines:
        if line.startswith("\\."):
            break
        values = line.rstrip("\n").split("\t")
        if len(values) == len(columns):
            row = dict(zip(columns, values))
            # Convert \N (NULL) to None
            row = {k: (None if v == "\\N" else v) for k, v in row.items()}
            rows.append(row)
    return rows


def extract_tables(sql_path: Path) -> tuple[list[dict], list[dict]]:
    """Extract RUBRIC and INFO tables from SQL dump."""

    # Regex to match COPY statements (handles public.tablename format)
    copy_pattern = re.compile(r"^COPY\s+(?:public\.)?(\w+)\s*\(([^)]+)\)")

    rubrics = []
    info = []

    opener = gzip.open if str(sql_path).endswith(".gz") else open

    with opener(sql_path, "rt", encoding="utf-8") as f:
        for line in f:
            match = copy_pattern.match(line)
            if match:
                table_name = match.group(1).lower()
                columns = [c.strip().lower() for c in match.group(2).split(",")]

                # Read following lines until we hit \.
                block_lines = []
                for data_line in f:
                    if data_line.startswith("\\."):
                        break
                    block_lines.append(data_line)

                if table_name == "rubric":
                    rubrics = parse_copy_block(block_lines, columns)
                    print(f"Found RUBRIC table: {len(rubrics)} rows, columns: {columns}")
                elif table_name == "info":
                    info = parse_copy_block(block_lines, columns)
                    print(f"Found INFO table: {len(info)} rows")

    return rubrics, info


def build_dataframe(rubrics: list[dict], info: list[dict], repertory: str) -> pd.DataFrame:
    """Build DataFrame filtering to specified repertory and deriving chapter from fullpath."""

    # Build DataFrame
    df = pd.DataFrame(rubrics)

    # Print repertory info
    print(f"\nAvailable repertories:")
    for row in info:
        print(f"  - {row['abbrev']}: {row['displaytitle']} ({row['languag']})")

    # Filter to specified repertory
    df = df[df["abbrev"] == repertory].copy()
    print(f"\nFiltered to '{repertory}': {len(df):,} rubrics")

    # Derive chapter from fullpath (first element before comma)
    def extract_chapter(fullpath):
        if fullpath and "," in fullpath:
            return fullpath.split(",")[0].strip()
        return fullpath

    df["chapter"] = df["fullpath"].apply(extract_chapter)

    # Rename columns to be clearer
    column_mapping = {
        "id": "id",
        "fullpath": "fullpath",
        "path": "path",
        "textt": "text",
        "chapterid": "chapter_id",
        "mother": "mother_id",
        "ismother": "is_mother",
        "abbrev": "repertory"
    }
    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

    # Select and order columns
    output_columns = ["id", "fullpath", "chapter"]
    available = [c for c in output_columns if c in df.columns]
    df = df[available]

    return df


def main():
    sql_path = DATA_DIR / "oorep.sql.gz"

    if not sql_path.exists():
        print(f"Error: {sql_path} not found. Run download_dump.py first.")
        return

    print(f"Parsing {sql_path}...")
    rubrics, info = extract_tables(sql_path)

    if not rubrics:
        print("Error: No rubrics found in dump!")
        return

    print(f"\nBuilding DataFrame...")
    df = build_dataframe(rubrics, info, REPERTORY)

    if df.empty:
        print(f"Error: No rubrics found for repertory '{REPERTORY}'")
        return

    # Summary statistics
    print(f"\n{'='*60}")
    print(f"EXTRACTION SUMMARY")
    print(f"{'='*60}")
    print(f"Total rubrics: {len(df):,}")
    print(f"\nRubrics by chapter:")
    print(df["chapter"].value_counts().to_string())

    # Save to Excel
    excel_path = DATA_DIR / "rubrics.xlsx"
    df.to_excel(excel_path, index=False)
    print(f"\nSaved to {excel_path}")

    # Show sample rows
    print(f"\n{'='*60}")
    print("SAMPLE RUBRICS (first 20)")
    print(f"{'='*60}")
    pd.set_option('display.max_colwidth', 100)
    pd.set_option('display.width', 200)
    print(df.head(20).to_string(index=False))

    # Show some Mind chapter examples
    mind_df = df[df["chapter"] == "Mind"]
    if not mind_df.empty:
        print(f"\n{'='*60}")
        print(f"MIND CHAPTER SAMPLES ({len(mind_df):,} total)")
        print(f"{'='*60}")
        print(mind_df.head(30).to_string(index=False))


if __name__ == "__main__":
    main()
