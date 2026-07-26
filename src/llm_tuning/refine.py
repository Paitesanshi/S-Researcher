from __future__ import annotations

import argparse
import os
from typing import Any

from io_utils import read_records, write_jsonl


SYSTEM_PROMPT = """You improve LLM-agent decisions for social simulations.
Return only a corrected decision. Preserve the requested output format,
scenario constraints, and agent identity. Address the evaluator feedback
without adding commentary."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refine low-rated decisions with any OpenAI-compatible API."
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--threshold", type=float, default=3.0)
    parser.add_argument(
        "--model",
        default=os.getenv("OPENAI_MODEL"),
        help="API model name; defaults to OPENAI_MODEL.",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("OPENAI_BASE_URL"),
        help="Optional OpenAI-compatible base URL.",
    )
    parser.add_argument("--temperature", type=float, default=0.0)
    return parser.parse_args()


def build_prompt(item: dict[str, Any]) -> str:
    return (
        f"Original prompt:\n{item['prompt']}\n\n"
        f"Original decision:\n{item['output']}\n\n"
        f"Evaluator reason:\n{item.get('reason', 'No reason supplied.')}\n\n"
        "Produce the corrected decision:"
    )


def main() -> None:
    args = parse_args()
    if not args.model:
        raise SystemExit("Set --model or OPENAI_MODEL.")
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required.")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit(
            "Install the tuning requirements before running refinement."
        ) from exc

    client_kwargs: dict[str, Any] = {"api_key": os.environ["OPENAI_API_KEY"]}
    if args.base_url:
        client_kwargs["base_url"] = args.base_url
    client = OpenAI(**client_kwargs)

    records = read_records(args.input)
    refined = []
    for index, item in enumerate(records, start=1):
        updated = dict(item)
        try:
            rating = float(item["rating"])
        except (KeyError, TypeError, ValueError):
            refined.append(updated)
            continue

        if (
            rating <= args.threshold
            and isinstance(item.get("prompt"), str)
            and isinstance(item.get("output"), str)
        ):
            response = client.chat.completions.create(
                model=args.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_prompt(item)},
                ],
                temperature=args.temperature,
            )
            updated["feedback"] = response.choices[0].message.content.strip()
            print(f"Refined record {index}/{len(records)}")
        refined.append(updated)

    write_jsonl(refined, args.output)
    print(f"Wrote {len(refined)} records to {args.output}")


if __name__ == "__main__":
    main()

