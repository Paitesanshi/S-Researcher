from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_SCENARIO_FILES = (
    "actions.json",
    "events.json",
    "scene_info.json",
    "code/SimEnv.py",
)
FORBIDDEN_DIRECTORY_NAMES = {
    "__pycache__",
    "datasets",
    "events",
    "log",
    "logs",
    "metrics_plots",
    "runs",
}
FORBIDDEN_SUFFIXES = {
    ".csv",
    ".dta",
    ".ipynb",
    ".log",
    ".pdf",
    ".pickle",
    ".pkl",
    ".png",
    ".pyc",
    ".svg",
    ".xlsx",
}
SKIPPED_DIRECTORY_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "artifacts",
    "build",
    "dist",
    "projects",
}


def is_skipped(relative: Path) -> bool:
    """Return whether a path belongs to local or generated workspace state."""
    return any(
        part in SKIPPED_DIRECTORY_NAMES or part.endswith(".egg-info")
        for part in relative.parts
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the code-only paper submission."
    )
    parser.add_argument(
        "--strict-scenarios",
        action="store_true",
        help="Fail when any declared paper scenario is missing source code.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    env_root = root / "src" / "envs"
    manifest_path = env_root / "paper_scenarios.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scenarios = [
        scenario
        for domain_scenarios in manifest["domains"].values()
        for scenario in domain_scenarios
    ]
    errors: list[str] = []
    warnings: list[str] = []

    if len(scenarios) != 50 or len(set(scenarios)) != 50:
        errors.append("The paper scenario manifest must contain 50 unique names.")

    incomplete = set(manifest.get("source_notes", {}))
    for scenario in scenarios:
        scenario_dir = env_root / scenario
        missing = [
            relative
            for relative in REQUIRED_SCENARIO_FILES
            if not (scenario_dir / relative).is_file()
        ]
        if missing:
            message = f"{scenario}: missing {', '.join(missing)}"
            if scenario in incomplete and not args.strict_scenarios:
                warnings.append(message)
            else:
                errors.append(message)

    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if is_skipped(relative):
            continue
        if path.is_dir() and path.name in FORBIDDEN_DIRECTORY_NAMES:
            if "src/envs" in relative.as_posix():
                errors.append(f"Forbidden generated directory: {relative}")
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            errors.append(f"Forbidden non-code artifact: {relative}")
        if path.suffix.lower() == ".json":
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                errors.append(f"Invalid JSON {relative}: {exc}")
        elif path.suffix.lower() == ".py":
            try:
                compile(path.read_text(encoding="utf-8"), str(relative), "exec")
            except (UnicodeDecodeError, SyntaxError) as exc:
                errors.append(f"Invalid Python {relative}: {exc}")

    print(f"Declared paper scenarios: {len(scenarios)}")
    print(f"Complete paper scenarios: {len(scenarios) - len(warnings)}")
    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("Code-only submission validation passed.")


if __name__ == "__main__":
    main()
