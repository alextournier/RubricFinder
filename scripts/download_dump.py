#!/usr/bin/env python3
"""Download the OOREP PostgreSQL dump from GitHub."""

import urllib.request
from pathlib import Path

DUMP_URL = "https://github.com/nondeterministic/oorep/raw/master/oorep.sql.gz"
DATA_DIR = Path(__file__).parent.parent / "data"


def download_dump():
    """Download oorep.sql.gz if not already present."""
    DATA_DIR.mkdir(exist_ok=True)
    output_path = DATA_DIR / "oorep.sql.gz"

    if output_path.exists():
        print(f"File already exists: {output_path} ({output_path.stat().st_size / 1024 / 1024:.1f} MB)")
        return output_path

    print(f"Downloading {DUMP_URL}...")
    urllib.request.urlretrieve(DUMP_URL, output_path)
    print(f"Downloaded to {output_path} ({output_path.stat().st_size / 1024 / 1024:.1f} MB)")
    return output_path


if __name__ == "__main__":
    download_dump()
