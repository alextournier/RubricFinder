#!/usr/bin/env python3
"""
Translate rubrics from archaic to modern English using LLM.
Adds translation + 10 test sentences as columns to mind_rubrics.xlsx.
Skips rows that already have translations (incremental).
"""

import os
import sys
import pandas as pd
from anthropic import Anthropic
from tqdm import tqdm

# Config
INPUT_FILE = "data/mind_rubrics.xlsx"
BATCH_SIZE = 20  # Process this many at a time, save after each batch
MODEL = "claude-3-haiku-20240307"


def get_translation_prompt(rubric_path: str) -> str:
    return f"""You are translating homeopathic repertory rubrics to clear modern English.

## Rubric Format Rules
Rubrics use comma-separated hierarchical paths from general to specific:
- "Mind, fear, dark" = fear of the dark
- "Mind, anxiety, menses, during" = anxiety occurring during menstruation

Key conventions:
- "of" suffix refers back to parent: "Mind, fear, death, of" = fear OF death
- "agg." = aggravation (symptom is worse from this)
- "amel." = amelioration (symptom is better from this)
- Time modifiers: "morning", "11 a.m.", "eating, after" = when symptom occurs
- Subrubrics inherit context from parents

## Translation Guidelines
- Preserve the original meaning exactly — only add clarity, never remove details
- Keep important terminology (e.g., specific fears, delusions, behaviors)
- Write a direct phrase describing the mental state, NOT "This rubric indicates..." or "The patient..."

Rubric: {rubric_path}

Provide:
1. A concise translation (short phrase). Examples:
   Good: "a tendency to start fires" or "fear of being alone"
   Bad: "This rubric indicates a person who..." or "The patient experiences..."
2. Ten different ways a patient might describe this symptom in everyday language

Format your response exactly like this:
TRANSLATION: [your translation]
TEST_1: [first patient description]
TEST_2: [second patient description]
TEST_3: [third patient description]
TEST_4: [fourth patient description]
TEST_5: [fifth patient description]
TEST_6: [sixth patient description]
TEST_7: [seventh patient description]
TEST_8: [eighth patient description]
TEST_9: [ninth patient description]
TEST_10: [tenth patient description]"""


def parse_response(response_text: str) -> dict:
    """Parse LLM response into translation and test sentences."""
    result = {"translation": "", **{f"test_{i}": "" for i in range(1, 11)}}

    for line in response_text.strip().split("\n"):
        line = line.strip()
        if line.startswith("TRANSLATION:"):
            result["translation"] = line.replace("TRANSLATION:", "").strip()
        elif line.startswith("TEST_"):
            for i in range(1, 11):
                prefix = f"TEST_{i}:"
                if line.startswith(prefix):
                    result[f"test_{i}"] = line.replace(prefix, "").strip()
                    break

    return result


def translate_rubric(client: Anthropic, rubric_path: str) -> dict:
    """Call LLM to translate a single rubric."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=500,
        messages=[{"role": "user", "content": get_translation_prompt(rubric_path)}]
    )
    return parse_response(response.content[0].text)


def main(limit: int = None):
    # Check API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    client = Anthropic(api_key=api_key)

    # Load data
    df = pd.read_excel(INPUT_FILE)
    print(f"Loaded {len(df)} rubrics from {INPUT_FILE}")

    # Find rows needing translation (empty translation column)
    needs_translation = df[df["translation"].isna() | (df["translation"] == "")]
    print(f"Rows needing translation: {len(needs_translation)}")

    if limit:
        needs_translation = needs_translation.head(limit)
        print(f"Limiting to {limit} rows for this run")

    if len(needs_translation) == 0:
        print("All rows already translated!")
        return

    # Process with progress bar
    translated = 0
    pbar = tqdm(needs_translation.index, desc="Translating", unit="rubric")
    for idx in pbar:
        rubric_path = df.at[idx, "path"]
        pbar.set_postfix_str(rubric_path[:40])

        try:
            result = translate_rubric(client, rubric_path)
            df.at[idx, "translation"] = result["translation"]
            for i in range(1, 11):
                df.at[idx, f"test_{i}"] = result[f"test_{i}"]
            translated += 1

            # Save after each batch
            if translated % BATCH_SIZE == 0:
                df.to_excel(INPUT_FILE, index=False)

        except Exception as e:
            tqdm.write(f"Error on {rubric_path}: {e}")
            break

    # Final save
    df.to_excel(INPUT_FILE, index=False)
    print(f"\nDone! Translated {translated} rubrics. Saved to {INPUT_FILE}")


if __name__ == "__main__":
    # Accept optional limit argument
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    main(limit)
