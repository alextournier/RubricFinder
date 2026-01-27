#!/usr/bin/env python3
"""
Translate rubrics from archaic to modern English using LLM.
Adds translation + 10 test sentences as columns to mind_rubrics.xlsx.
Skips rows that already have translations (incremental).
Supports parallel processing with asyncio for ~10x speedup.
"""

import asyncio
import os
import sys
import pandas as pd
from openai import AsyncOpenAI, OpenAI
from tqdm import tqdm
from tqdm.asyncio import tqdm as async_tqdm

# Config
INPUT_FILE = "data/mind_rubrics.xlsx"
BATCH_SIZE = 20  # Save after this many translations
CONCURRENT_REQUESTS = 10  # Max parallel API calls (conservative for rate limits)
MODEL = "gpt-4o-mini"  # Testing model (claude-sonnet-4-20250514 for production)


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

## Critical Patterns (often mistranslated)

**"ailments after X"** = symptoms/illness CAUSED BY the event X
- "anger, ailments after anger" = health problems that develop as a consequence of experiencing anger
- NOT "tendency to be angry" — it's about what happens AFTER the anger

**"speech, answers, ..."** = specifically about HOW the person answers questions
- "speech, answers, monosyllable" = answers questions with single words
- "speech, answers, stupor returns quickly, after" = after answering, returns to stupor
- Always preserve the "answering questions" context

**Archaic word order** — read carefully, don't assume modern grammar
- "stabbed, so that he could have, any one" = anger so intense he could have stabbed anyone
- NOT "feels like being stabbed"

**", after" suffix** = indicates what happens AFTER the preceding event
- "stupor returns quickly, after" = stupor returns quickly after (answering)
- NOT "recovery from stupor"

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


def translate_rubric(client: OpenAI, rubric_path: str) -> dict:
    """Call LLM to translate a single rubric (sync version)."""
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=500,
        messages=[{"role": "user", "content": get_translation_prompt(rubric_path)}]
    )
    return parse_response(response.choices[0].message.content)


async def translate_rubric_async(
    client: AsyncOpenAI, semaphore: asyncio.Semaphore, rubric_path: str, idx: int
) -> tuple[int, dict | Exception]:
    """Call LLM to translate a single rubric (async version with rate limiting)."""
    async with semaphore:
        try:
            response = await client.chat.completions.create(
                model=MODEL,
                max_tokens=500,
                messages=[{"role": "user", "content": get_translation_prompt(rubric_path)}]
            )
            return idx, parse_response(response.choices[0].message.content)
        except Exception as e:
            return idx, e


async def translate_batch_async(
    client: AsyncOpenAI,
    semaphore: asyncio.Semaphore,
    rubrics: list[tuple[int, str]],
) -> list[tuple[int, dict | Exception]]:
    """Translate a batch of rubrics concurrently."""
    tasks = [
        translate_rubric_async(client, semaphore, path, idx)
        for idx, path in rubrics
    ]
    return await asyncio.gather(*tasks)


async def main_async(limit: int = None, concurrency: int = CONCURRENT_REQUESTS):
    """Async main function for parallel translation."""
    # Check API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        sys.exit(1)

    client = AsyncOpenAI(api_key=api_key)
    semaphore = asyncio.Semaphore(concurrency)

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

    print(f"Using {concurrency} concurrent requests")

    # Prepare list of (idx, path) tuples
    work_items = [(idx, df.at[idx, "path"]) for idx in needs_translation.index]

    # Process in batches for incremental saves
    translated = 0
    errors = 0
    pbar = tqdm(total=len(work_items), desc="Translating", unit="rubric")

    for batch_start in range(0, len(work_items), BATCH_SIZE):
        batch = work_items[batch_start : batch_start + BATCH_SIZE]
        results = await translate_batch_async(client, semaphore, batch)

        for idx, result in results:
            if isinstance(result, Exception):
                tqdm.write(f"Error on {df.at[idx, 'path']}: {result}")
                errors += 1
            else:
                df.at[idx, "translation"] = result["translation"]
                for i in range(1, 11):
                    df.at[idx, f"test_{i}"] = result[f"test_{i}"]
                translated += 1
            pbar.update(1)

        # Save after each batch
        df.to_excel(INPUT_FILE, index=False)

    pbar.close()
    print(f"\nDone! Translated {translated} rubrics ({errors} errors). Saved to {INPUT_FILE}")


def main(limit: int = None):
    """Sync main function (legacy, for backwards compatibility)."""
    # Check API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

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
    import argparse

    parser = argparse.ArgumentParser(description="Translate rubrics using LLM")
    parser.add_argument("limit", nargs="?", type=int, help="Max rubrics to translate")
    parser.add_argument("--sync", action="store_true", help="Use sequential (non-parallel) mode")
    parser.add_argument(
        "--concurrency", "-c", type=int, default=CONCURRENT_REQUESTS,
        help=f"Number of concurrent requests (default: {CONCURRENT_REQUESTS})"
    )
    args = parser.parse_args()

    if args.sync:
        main(args.limit)
    else:
        asyncio.run(main_async(args.limit, args.concurrency))
