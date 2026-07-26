from __future__ import annotations

import argparse
import random
from collections import defaultdict
from typing import Any

from io_utils import read_records, write_jsonl


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def prepare_sft(
    records: list[dict[str, Any]], min_rating: float | None
) -> list[dict[str, str]]:
    prepared = []
    for item in records:
        if not _nonempty(item.get("prompt")):
            continue
        if min_rating is not None:
            try:
                if float(item["rating"]) < min_rating:
                    continue
            except (KeyError, TypeError, ValueError):
                continue
        completion = item.get("feedback") if _nonempty(item.get("feedback")) else item.get("output")
        if _nonempty(completion):
            prepared.append(
                {"prompt": item["prompt"].strip(), "completion": completion.strip()}
            )
    return prepared


def prepare_dpo(records: list[dict[str, Any]]) -> list[dict[str, str]]:
    prepared: list[dict[str, str]] = []
    rating_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for item in records:
        prompt = item.get("prompt")
        if not _nonempty(prompt):
            continue

        if _nonempty(item.get("chosen")) and _nonempty(item.get("rejected")):
            prepared.append(
                {
                    "prompt": prompt.strip(),
                    "chosen": item["chosen"].strip(),
                    "rejected": item["rejected"].strip(),
                }
            )
        elif _nonempty(item.get("feedback")) and _nonempty(item.get("output")):
            prepared.append(
                {
                    "prompt": prompt.strip(),
                    "chosen": item["feedback"].strip(),
                    "rejected": item["output"].strip(),
                }
            )
        elif _nonempty(item.get("output")) and item.get("rating") is not None:
            rating_groups[prompt.strip()].append(item)

    for prompt, items in rating_groups.items():
        if len(items) < 2:
            continue
        try:
            ordered = sorted(items, key=lambda item: float(item["rating"]))
        except (TypeError, ValueError):
            continue
        if float(ordered[-1]["rating"]) == float(ordered[0]["rating"]):
            continue
        prepared.append(
            {
                "prompt": prompt,
                "chosen": ordered[-1]["output"].strip(),
                "rejected": ordered[0]["output"].strip(),
            }
        )
    return prepared


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert VR2T ratings and revisions into SFT or DPO JSONL."
    )
    parser.add_argument("--input", required=True, help="Input JSON or JSONL file.")
    parser.add_argument("--output", required=True, help="Output JSONL file.")
    parser.add_argument("--method", required=True, choices=("sft", "dpo"))
    parser.add_argument(
        "--min-rating",
        type=float,
        default=None,
        help="Optional minimum rating for SFT records.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-samples", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = read_records(args.input)
    if args.method == "sft":
        prepared = prepare_sft(records, args.min_rating)
    else:
        prepared = prepare_dpo(records)

    random.Random(args.seed).shuffle(prepared)
    if args.max_samples is not None:
        prepared = prepared[: args.max_samples]
    if not prepared:
        raise SystemExit("No valid training records were produced.")

    write_jsonl(prepared, args.output)
    print(f"Wrote {len(prepared)} {args.method.upper()} records to {args.output}")


if __name__ == "__main__":
    main()

