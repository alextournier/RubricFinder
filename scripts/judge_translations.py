#!/usr/bin/env python3
"""
LLM judge for translation quality.
Scores translations on detail preservation and accuracy.
"""

import argparse
import os
import sys
import re

import pandas as pd
from anthropic import Anthropic
from tqdm import tqdm


def get_judge_prompt(original: str, translation: str) -> str:
    """Prompt for LLM to judge translation quality."""
    return f"""You are evaluating a translation of a homeopathic rubric from archaic medical terminology to modern English.

ORIGINAL RUBRIC: {original}

TRANSLATION: {translation}

Score the translation on these criteria (1-5 scale each):

1. DETAIL_PRESERVATION: Are ALL details from the original preserved? (5 = all details kept, 1 = major details lost)
2. ACCURACY: Is the meaning correct? (5 = perfectly accurate, 1 = wrong meaning)
3. CLARITY: Is it clear and understandable? (5 = very clear, 1 = confusing)

Important scoring notes:
- Rubric paths use comma hierarchy (general → specific), e.g. "Mind, anxiety, forenoon" means anxiety specifically in the forenoon (late morning)
- "forenoon" = late morning (before noon), NOT just "morning"
- Abbreviations: agg. = worse from, amel. = better from
- Penalize translations that oversimplify or lose specific details

Respond in EXACTLY this format:
DETAIL_PRESERVATION: [1-5]
ACCURACY: [1-5]
CLARITY: [1-5]
COMMENT: [brief explanation of any issues]"""


def parse_judge_response(text: str) -> dict:
    """Parse judge response into scores."""
    result = {
        "detail_preservation": None,
        "accuracy": None,
        "clarity": None,
        "comment": ""
    }

    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith("DETAIL_PRESERVATION:"):
            match = re.search(r'(\d)', line)
            if match:
                result["detail_preservation"] = int(match.group(1))
        elif line.startswith("ACCURACY:"):
            match = re.search(r'(\d)', line)
            if match:
                result["accuracy"] = int(match.group(1))
        elif line.startswith("CLARITY:"):
            match = re.search(r'(\d)', line)
            if match:
                result["clarity"] = int(match.group(1))
        elif line.startswith("COMMENT:"):
            result["comment"] = line.replace("COMMENT:", "").strip()

    return result


def judge_translation(client: Anthropic, original: str, translation: str, model: str = "claude-3-haiku-20240307") -> dict:
    """Have LLM judge a single translation."""
    response = client.messages.create(
        model=model,
        max_tokens=200,
        messages=[{"role": "user", "content": get_judge_prompt(original, translation)}]
    )
    return parse_judge_response(response.content[0].text)


def main():
    parser = argparse.ArgumentParser(description="Judge translation quality with LLM")
    parser.add_argument("--input", type=str, default="tests/translation_cost_comparison.xlsx",
                        help="Input Excel file with translations")
    parser.add_argument("--output", type=str, default="tests/translation_scores.xlsx",
                        help="Output Excel file with scores")
    parser.add_argument("--judge-model", type=str, default="claude-3-haiku-20240307",
                        help="Model to use as judge")
    args = parser.parse_args()

    # Check API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    client = Anthropic(api_key=api_key)

    # Load translations
    df = pd.read_excel(args.input, sheet_name="Details")
    print(f"Loaded {len(df)} translations from {args.input}")

    # Judge each translation
    scores = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Judging"):
        if row["translation"].startswith("ERROR"):
            scores.append({
                "detail_preservation": None,
                "accuracy": None,
                "clarity": None,
                "total_score": None,
                "comment": "Skipped - translation error"
            })
            continue

        try:
            result = judge_translation(client, row["path"], row["translation"], args.judge_model)
            # Calculate total score (average)
            valid_scores = [v for v in [result["detail_preservation"], result["accuracy"], result["clarity"]] if v]
            result["total_score"] = round(sum(valid_scores) / len(valid_scores), 2) if valid_scores else None
            scores.append(result)
        except Exception as e:
            tqdm.write(f"Error judging {row['path'][:30]}: {e}")
            scores.append({
                "detail_preservation": None,
                "accuracy": None,
                "clarity": None,
                "total_score": None,
                "comment": f"Error: {e}"
            })

    # Add scores to dataframe
    scores_df = pd.DataFrame(scores)
    result_df = pd.concat([df, scores_df], axis=1)

    # Create summary by model
    summary_rows = []
    for model in result_df["model"].unique():
        model_data = result_df[result_df["model"] == model]
        valid = model_data.dropna(subset=["total_score"])
        if len(valid) == 0:
            continue
        summary_rows.append({
            "Model": model,
            "Avg Detail": round(valid["detail_preservation"].mean(), 2),
            "Avg Accuracy": round(valid["accuracy"].mean(), 2),
            "Avg Clarity": round(valid["clarity"].mean(), 2),
            "Avg Total": round(valid["total_score"].mean(), 2),
            "Sample Size": len(valid)
        })

    summary_df = pd.DataFrame(summary_rows)

    # Write output
    with pd.ExcelWriter(args.output, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        result_df.to_excel(writer, sheet_name="Details", index=False)

    print(f"\nResults saved to {args.output}")
    print("\n=== Summary ===")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
