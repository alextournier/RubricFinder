#!/usr/bin/env python3
"""
Regenerate test sentences for rubrics with emphasis on specificity.
Each sentence should uniquely match its rubric and not others.
"""

import asyncio
import os
import sys
import pandas as pd
from openai import AsyncOpenAI
from tqdm import tqdm

# Config
INPUT_FILE = "tests/test_sentences.xlsx"
RUBRICS_FILE = "data/mind_rubrics.xlsx"
OUTPUT_FILE = "tests/test_sentences.xlsx"
CONCURRENT_REQUESTS = 10
MODEL = "gpt-4o-mini"


def get_test_sentences_prompt(rubric_path: str, translation: str) -> str:
    return f"""Generate 10 SHORT test sentences for semantic search evaluation.

## Task
Create 10 brief paraphrases of this symptom using everyday language.
These will test if semantic search matches the translation embedding.

## Critical: Keep Sentences SHORT and DIRECT
- Maximum 8-10 words per sentence
- Use simple vocabulary close to the translation
- No elaborate stories or extra details
- Focus on the CORE meaning only

## Examples
Translation: "a tendency to start fires"
GOOD: "I have urges to start fires", "compelled to set things ablaze", "drawn to starting fires"
BAD: "I often find myself wanting to set things on fire, like old papers or pieces of wood in the backyard" (too long)

Translation: "fear of the dark"
GOOD: "darkness scares me", "I'm terrified of the dark", "afraid when it's dark"
BAD: "I can't sleep without a light on because darkness terrifies me" (too elaborate)

Translation: "sudden changes in mood"
GOOD: "my mood shifts abruptly", "quick mood swings", "emotions change suddenly"

## Rubric Information
Path: {rubric_path}
Translation: {translation}

## Output Format
10 lines, numbered 1-10. Keep each under 10 words:
1: [short paraphrase]
2: [short paraphrase]
3: [short paraphrase]
4: [short paraphrase]
5: [short paraphrase]
6: [short paraphrase]
7: [short paraphrase]
8: [short paraphrase]
9: [short paraphrase]
10: [short paraphrase]"""


def parse_response(response_text: str) -> dict:
    """Parse LLM response into test sentences."""
    result = {f"test_{i}": "" for i in range(1, 11)}

    for line in response_text.strip().split("\n"):
        line = line.strip()
        for i in range(1, 11):
            prefixes = [f"{i}:", f"{i}.", f"{i})"]
            for prefix in prefixes:
                if line.startswith(prefix):
                    result[f"test_{i}"] = line[len(prefix):].strip()
                    break

    return result


async def generate_sentences_async(
    client: AsyncOpenAI,
    semaphore: asyncio.Semaphore,
    rubric_path: str,
    translation: str,
    idx: int
) -> tuple[int, dict | Exception]:
    """Generate test sentences for a single rubric."""
    async with semaphore:
        try:
            response = await client.chat.completions.create(
                model=MODEL,
                max_tokens=600,
                messages=[{"role": "user", "content": get_test_sentences_prompt(rubric_path, translation)}]
            )
            return idx, parse_response(response.choices[0].message.content)
        except Exception as e:
            return idx, e


async def main():
    # Check API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        sys.exit(1)

    client = AsyncOpenAI(api_key=api_key)
    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

    # Load existing test sentences file (has the 120 rubric IDs)
    df = pd.read_excel(INPUT_FILE)
    print(f"Loaded {len(df)} rubrics from {INPUT_FILE}")

    # Load rubrics file to get translations
    rubrics_df = pd.read_excel(RUBRICS_FILE)
    rubrics_df = rubrics_df.set_index("id")

    # Add translation column if not present
    if "translation" not in df.columns:
        df["translation"] = df["id"].map(rubrics_df["translation"])

    # Prepare work items
    work_items = []
    for idx, row in df.iterrows():
        rubric_id = row["id"]
        path = row["path"]
        # Get translation from rubrics file
        translation = rubrics_df.loc[rubric_id, "translation"] if rubric_id in rubrics_df.index else ""
        if pd.isna(translation):
            translation = path  # fallback to path
        work_items.append((idx, path, translation))

    print(f"Generating test sentences for {len(work_items)} rubrics...")

    # Process all concurrently
    tasks = [
        generate_sentences_async(client, semaphore, path, translation, idx)
        for idx, path, translation in work_items
    ]

    results = []
    for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Generating"):
        result = await coro
        results.append(result)

    # Apply results
    success = 0
    errors = 0
    for idx, result in results:
        if isinstance(result, Exception):
            print(f"Error at index {idx}: {result}")
            errors += 1
        else:
            for col, val in result.items():
                df.at[idx, col] = val
            success += 1

    print(f"\nCompleted: {success} success, {errors} errors")

    # Save
    df.to_excel(OUTPUT_FILE, index=False)
    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
