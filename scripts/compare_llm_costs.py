#!/usr/bin/env python3
"""
Compare translation costs across different LLMs.
Benchmarks Claude and OpenAI models on a sample of rubrics.
"""

import argparse
import os
import sys
from datetime import datetime

import pandas as pd
from tqdm import tqdm

# Model pricing (USD per million tokens)
MODEL_PRICING = {
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
}

INPUT_FILE = "data/mind_rubrics.xlsx"


def get_translation_prompt(rubric_path: str) -> str:
    """Same prompt as translate_rubrics.py for consistency."""
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


def translate_anthropic(client, model: str, prompt: str) -> tuple[str, int, int]:
    """Call Anthropic API and return (text, input_tokens, output_tokens)."""
    response = client.messages.create(
        model=model,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return (
        response.content[0].text,
        response.usage.input_tokens,
        response.usage.output_tokens
    )


def translate_openai(client, model: str, prompt: str) -> tuple[str, int, int]:
    """Call OpenAI API and return (text, input_tokens, output_tokens)."""
    response = client.chat.completions.create(
        model=model,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return (
        response.choices[0].message.content,
        response.usage.prompt_tokens,
        response.usage.completion_tokens
    )


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD for given token counts."""
    pricing = MODEL_PRICING[model]
    return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000


def run_benchmark(rubrics: pd.DataFrame, models: list[str], anthropic_client, openai_client) -> list[dict]:
    """Run translations across all models and rubrics, return results."""
    results = []

    total_iterations = len(rubrics) * len(models)
    pbar = tqdm(total=total_iterations, desc="Benchmarking", unit="call")

    for _, row in rubrics.iterrows():
        rubric_id = row["id"]
        path = row["path"]
        prompt = get_translation_prompt(path)

        for model in models:
            pbar.set_postfix_str(f"{model[:15]}...")

            try:
                if model.startswith("claude"):
                    if anthropic_client is None:
                        pbar.update(1)
                        continue
                    text, input_tok, output_tok = translate_anthropic(anthropic_client, model, prompt)
                else:
                    if openai_client is None:
                        pbar.update(1)
                        continue
                    text, input_tok, output_tok = translate_openai(openai_client, model, prompt)

                parsed = parse_response(text)
                cost = calculate_cost(model, input_tok, output_tok)

                results.append({
                    "rubric_id": rubric_id,
                    "path": path,
                    "model": model,
                    "translation": parsed["translation"],
                    "input_tokens": input_tok,
                    "output_tokens": output_tok,
                    "cost_usd": cost,
                })

            except Exception as e:
                tqdm.write(f"Error on {model} / {path[:30]}: {e}")
                results.append({
                    "rubric_id": rubric_id,
                    "path": path,
                    "model": model,
                    "translation": f"ERROR: {e}",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0,
                })

            pbar.update(1)

    pbar.close()
    return results


def generate_report(results: list[dict], output_path: str, mind_count: int = 5900, full_count: int = 74600):
    """Generate Excel report with Summary and Details sheets."""
    df = pd.DataFrame(results)

    # Filter out errors for statistics
    valid = df[~df["translation"].str.startswith("ERROR", na=False)]

    # Build summary statistics per model
    summary_rows = []
    models = df["model"].unique()

    for model in models:
        model_data = valid[valid["model"] == model]
        if len(model_data) == 0:
            continue

        avg_input = model_data["input_tokens"].mean()
        avg_output = model_data["output_tokens"].mean()
        avg_cost = model_data["cost_usd"].mean()

        summary_rows.append({
            "Model": model,
            "Avg Input Tokens": round(avg_input, 1),
            "Avg Output Tokens": round(avg_output, 1),
            "Avg Cost/Rubric ($)": round(avg_cost, 6),
            f"Est. Cost {mind_count:,} Mind ($)": round(avg_cost * mind_count, 2),
            f"Est. Cost {full_count:,} Full ($)": round(avg_cost * full_count, 2),
            "Sample Size": len(model_data),
        })

    summary_df = pd.DataFrame(summary_rows)

    # Write to Excel with two sheets
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        df.to_excel(writer, sheet_name="Details", index=False)

    return summary_df


def main():
    parser = argparse.ArgumentParser(description="Compare LLM translation costs")
    parser.add_argument("--sample", type=int, default=30, help="Number of rubrics to sample (default: 30)")
    parser.add_argument("--output", type=str, default="tests/translation_cost_comparison.xlsx", help="Output Excel file")
    parser.add_argument("--models", type=str, nargs="+",
                        default=list(MODEL_PRICING.keys()),
                        help="Models to benchmark (default: all)")
    args = parser.parse_args()

    # Check API keys
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    anthropic_client = None
    openai_client = None

    if anthropic_key:
        from anthropic import Anthropic
        anthropic_client = Anthropic(api_key=anthropic_key)
        print("Anthropic API key found")
    else:
        print("Warning: ANTHROPIC_API_KEY not set - skipping Claude models")

    if openai_key:
        from openai import OpenAI
        openai_client = OpenAI(api_key=openai_key)
        print("OpenAI API key found")
    else:
        print("Warning: OPENAI_API_KEY not set - skipping GPT models")

    if not anthropic_client and not openai_client:
        print("Error: No API keys found. Set ANTHROPIC_API_KEY and/or OPENAI_API_KEY")
        sys.exit(1)

    # Filter models based on available clients
    models = []
    for m in args.models:
        if m.startswith("claude") and anthropic_client:
            models.append(m)
        elif m.startswith("gpt") and openai_client:
            models.append(m)

    if not models:
        print("Error: No models available with current API keys")
        sys.exit(1)

    print(f"Models to benchmark: {models}")

    # Load rubrics and sample
    df = pd.read_excel(INPUT_FILE)
    sample = df.sample(n=min(args.sample, len(df)), random_state=42)
    print(f"Sampling {len(sample)} rubrics from {len(df)} total")

    # Run benchmark
    results = run_benchmark(sample, models, anthropic_client, openai_client)

    # Generate report
    summary = generate_report(results, args.output)
    print(f"\nResults saved to {args.output}")
    print("\n=== Summary ===")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
