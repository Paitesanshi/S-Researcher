from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one reproducible VR2T refinement and tuning round."
    )
    parser.add_argument("--ratings", required=True, help="Rated decision JSON/JSONL.")
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--method", choices=("sft", "dpo"), required=True)
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument(
        "--refine",
        action="store_true",
        help="Refine low-rated samples through an OpenAI-compatible API.",
    )
    parser.add_argument("--threshold", type=float, default=3.0)
    return parser.parse_args()


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True)


def main() -> None:
    args = parse_args()
    module_dir = Path(__file__).resolve().parent
    round_dir = Path(args.work_dir) / f"round_{args.round}"
    round_dir.mkdir(parents=True, exist_ok=True)
    refined = round_dir / "refined.jsonl"
    dataset = round_dir / f"{args.method}.jsonl"
    adapter = round_dir / f"{args.method}_adapter"

    source = Path(args.ratings)
    if args.refine:
        run(
            [
                sys.executable,
                str(module_dir / "refine.py"),
                "--input",
                str(source),
                "--output",
                str(refined),
                "--threshold",
                str(args.threshold),
            ]
        )
        source = refined

    run(
        [
            sys.executable,
            str(module_dir / "prepare_data.py"),
            "--input",
            str(source),
            "--output",
            str(dataset),
            "--method",
            args.method,
        ]
    )
    run(
        [
            sys.executable,
            str(module_dir / "train.py"),
            "--config",
            args.config,
            "--dataset",
            str(dataset),
            "--output-dir",
            str(adapter),
            "--method",
            args.method,
        ]
    )


if __name__ == "__main__":
    main()

