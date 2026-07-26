from __future__ import annotations

import argparse
import csv
import json
import math
import random
import subprocess
import sys
from pathlib import Path
from typing import Any


TEACHER_POLICIES = {
    "expression": (
        "Prioritize confident verbal and non-verbal expression, including "
        "clear speech, eye contact, and assertive gestures."
    ),
    "merit": (
        "Prioritize demonstrated academic performance and the quality of the "
        "student's proposed answer."
    ),
    "socioeconomic": (
        "Prioritize cues associated with family resources and parental "
        "educational background."
    ),
}

PUBLIC_GOODS_CONDITIONS = {
    f"{mechanism}-{level_name}": (mechanism, contribution)
    for mechanism in ("voluntary", "forced")
    for level_name, contribution in (("low", 2), ("medium", 5), ("high", 8))
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a paper case study.")
    parser.add_argument(
        "--case",
        required=True,
        choices=("cultural_dissemination", "teacher_attention", "public_goods"),
    )
    parser.add_argument("--condition")
    parser.add_argument("--replicate", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--model-config", default="config/model_config.json")
    parser.add_argument("--model-config-name")
    parser.add_argument("--artifact-root", default="artifacts/paper_cases")
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Write profiles and config without starting the simulation.",
    )
    return parser.parse_args()


def write_json(value: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)


def write_relationships(
    rows: list[tuple[str, str, str, str]], path: Path
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["source_id", "target_id", "relationship_type", "direction"]
        )
        writer.writerows(rows)


def grid_relationships(count: int) -> list[tuple[str, str, str, str]]:
    side = math.isqrt(count)
    if side * side != count:
        raise ValueError("Cultural-agent count must form a square grid.")
    rows: list[tuple[str, str, str, str]] = []
    for row in range(side):
        for column in range(side):
            source = row * side + column
            if column + 1 < side:
                rows.append(
                    (str(source), str(source + 1), "grid_neighbor", "bidirectional")
                )
            if row + 1 < side:
                rows.append(
                    (
                        str(source),
                        str(source + side),
                        "grid_neighbor",
                        "bidirectional",
                    )
                )
    return rows


def cultural_profiles(count: int, rng: random.Random) -> list[dict[str, Any]]:
    options = {
        "music_preference": ["Classical", "Jazz", "Pop", "Folk", "Electronic"],
        "culinary_preference": ["Local", "International", "Vegetarian", "Traditional", "Fast Food"],
        "fashion_style": ["Formal", "Casual", "Athletic", "Traditional", "Alternative"],
        "political_orientation": ["Progressive", "Centrist", "Conservative", "Green", "Libertarian"],
        "leisure_activity": ["Arts", "Sports", "Outdoors", "Reading", "Media"],
        "personality_trait": ["open", "neutral", "traditional"],
    }
    profiles = []
    for index in range(count):
        profile = {
            key: rng.choice(values)
            for key, values in options.items()
        }
        profile.update(
            {
                "id": str(index),
                "name": f"CulturalAgent_{index:04d}",
                "agent_type": "CulturalAgent",
                "trait_explanations": {},
                "recommendation_history": [],
                "adoption_history": [],
            }
        )
        profiles.append(profile)
    return profiles


def teacher_profiles(
    teacher_count: int,
    student_count: int,
    condition: str,
    rng: random.Random,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    policy = TEACHER_POLICIES[condition]
    teachers = [
        {
            "id": f"T_{index}",
            "agent_type": "TeacherAgent",
            "name": f"Teacher_{index:03d}",
            "class_id": str(index),
            "school_id": str(index // 5),
            "clsids": str(index),
            "schids": str(index // 5),
            "policy_mode": condition,
            "question_difficulty_default": 0.5,
            "decision_logic": policy,
        }
        for index in range(teacher_count)
    ]
    levels = ("low", "medium", "high")
    students = []
    for index in range(student_count):
        achievement = rng.choice(levels)
        expression = rng.choice(levels)
        socioeconomic = rng.choice(levels)
        students.append(
            {
                "id": f"S_{index}",
                "agent_type": "StudentAgent",
                "name": f"Student_{index:05d}",
                "class_id": str(index % teacher_count),
                "school_id": str((index % teacher_count) // 5),
                "prompt_summary": (
                    f"Academic performance is {achievement}; communication "
                    f"is {expression}; socioeconomic background is "
                    f"{socioeconomic}; migration status is unknown."
                ),
                "observed_outcomes": {},
            }
        )
    return teachers, students


def public_goods_profiles(
    follower_count: int, condition: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    mechanism, contribution = PUBLIC_GOODS_CONDITIONS[condition]
    leaders = [
        {
            "id": "leader_0",
            "name": "Leader",
            "agent_type": "LeaderAgent",
            "decision_mechanism": mechanism,
            "contribution_level": contribution,
            "interaction_history": [],
        }
    ]
    followers = [
        {
            "id": f"follower_{index}",
            "name": f"Follower_{index:03d}",
            "agent_type": "FollowerAgent",
            "trait": "Prosocial" if index % 2 == 0 else "Proself",
        }
        for index in range(follower_count)
    ]
    return leaders, followers


def base_config(
    env_name: str,
    max_steps: int,
    seed: int,
    profiles: dict[str, dict[str, Any]],
    relationship_path: Path,
) -> dict[str, Any]:
    return {
        "simulator": {
            "environment": {
                "name": env_name,
                "mode": "round",
                "max_steps": max_steps,
                "interval": 0.0,
                "bus_idle_timeout": 120.0,
                "export_training_data": False,
                "export_event_data": False,
                "collection_interval": 1,
                "additional_config": {
                    "export_event_flow": False,
                    "random_seed": seed,
                },
            }
        },
        "agent": {
            "profile": profiles,
            "relationship_path": str(relationship_path.resolve()),
            "memory": {
                "strategy": "ShortLongStrategy",
                "storages": {
                    "short_term_storage": {
                        "class": "ListMemoryStorage",
                        "capacity": 100,
                    }
                },
                "metric_weights": {"recency": 1.0},
                "transfer_conditions": {},
                "operations": {
                    "add": {"class": "AddMemoryOperation"},
                    "retrieve": {"class": "RetrieveMemoryOperation"},
                    "remove": {"class": "RemoveMemoryOperation"},
                },
                "metrics": {
                    "recency": {"class": "RecencyMetric", "weight": 1.0}
                },
            },
        },
        "database": {"enabled": False},
        "distribution": {"enabled": False, "mode": "single"},
        "monitor": {"enabled": True, "update_interval": 1},
        "random_seed": seed,
    }


def prepare(args: argparse.Namespace, repo_root: Path) -> tuple[str, Path, Path]:
    seed_base = 56_788 if args.case == "teacher_attention" else 10_000
    seed = seed_base + args.replicate
    rng = random.Random(seed)
    condition = args.condition or "baseline"
    run_dir = (
        repo_root
        / args.artifact_root
        / args.case
        / condition
        / f"replicate_{args.replicate}"
    ).resolve()
    profile_dir = run_dir / "profiles"

    if args.case == "cultural_dissemination":
        if args.condition:
            raise SystemExit("cultural_dissemination does not use --condition.")
        env_name = "dynamic_culture_dissemination"
        count = 16 if args.smoke else 100
        profiles = cultural_profiles(count, rng)
        profile_path = profile_dir / "CulturalAgent.json"
        relationship_path = profile_dir / "Relationship.csv"
        write_json(profiles, profile_path)
        write_relationships(grid_relationships(count), relationship_path)
        profile_config = {
            "CulturalAgent": {
                "count": count,
                "profile_path": str(profile_path),
            }
        }
        config = base_config(
            env_name,
            2 if args.smoke else 100,
            seed,
            profile_config,
            relationship_path,
        )

    elif args.case == "teacher_attention":
        condition = args.condition or "expression"
        if condition not in TEACHER_POLICIES:
            choices = ", ".join(TEACHER_POLICIES)
            raise SystemExit(f"Teacher condition must be one of: {choices}")
        env_name = "teacher_attention_allocation"
        teacher_count, student_count = ((1, 10) if args.smoke else (221, 5525))
        teachers, students = teacher_profiles(
            teacher_count, student_count, condition, rng
        )
        teacher_path = profile_dir / "TeacherAgent.json"
        student_path = profile_dir / "StudentAgent.json"
        relationship_path = profile_dir / "Relationship.csv"
        write_json(teachers, teacher_path)
        write_json(students, student_path)
        write_relationships(
            [
                (
                    f"T_{student_index % teacher_count}",
                    f"S_{student_index}",
                    "teacher_student",
                    "bidirectional",
                )
                for student_index in range(student_count)
            ],
            relationship_path,
        )
        profile_config = {
            "TeacherAgent": {
                "count": teacher_count,
                "profile_path": str(teacher_path),
            },
            "StudentAgent": {
                "count": student_count,
                "profile_path": str(student_path),
            },
        }
        config = base_config(
            env_name,
            2 if args.smoke else 30,
            seed,
            profile_config,
            relationship_path,
        )

    else:
        condition = args.condition or "voluntary-low"
        if condition not in PUBLIC_GOODS_CONDITIONS:
            choices = ", ".join(PUBLIC_GOODS_CONDITIONS)
            raise SystemExit(f"Public-goods condition must be one of: {choices}")
        env_name = "public_goods_leadership_dynamics"
        follower_count = 10 if args.smoke else 100
        leaders, followers = public_goods_profiles(follower_count, condition)
        leader_path = profile_dir / "LeaderAgent.json"
        follower_path = profile_dir / "FollowerAgent.json"
        relationship_path = profile_dir / "Relationship.csv"
        write_json(leaders, leader_path)
        write_json(followers, follower_path)
        write_relationships(
            [
                (
                    "leader_0",
                    f"follower_{index}",
                    "leadership",
                    "bidirectional",
                )
                for index in range(follower_count)
            ],
            relationship_path,
        )
        profile_config = {
            "LeaderAgent": {"count": 1, "profile_path": str(leader_path)},
            "FollowerAgent": {
                "count": follower_count,
                "profile_path": str(follower_path),
            },
        }
        config = base_config(
            env_name, 1, seed, profile_config, relationship_path
        )

    config_path = run_dir / "config.json"
    write_json(config, config_path)
    return env_name, config_path, run_dir


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    env_name, config_path, run_dir = prepare(args, repo_root)
    print(f"Prepared {args.case} in {run_dir}")
    if args.prepare_only:
        return

    model_config = Path(args.model_config)
    if not model_config.is_absolute():
        model_config = repo_root / model_config

    command = [
        sys.executable,
        str(repo_root / "src" / "main.py"),
        "--config",
        str(config_path),
        "--model_config",
        str(model_config.resolve()),
        "--env",
        env_name,
        "--output_dir",
        str(run_dir / "output"),
        "--log_dir",
        str(run_dir / "logs"),
    ]
    if args.model_config_name:
        command.extend(["--model_config_name", args.model_config_name])
    print("+", " ".join(command))
    subprocess.run(command, cwd=repo_root, check=True)


if __name__ == "__main__":
    main()
