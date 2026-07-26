"""Build de-identified teacher and student profiles from authorized CEPS files."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


MISSING_CODES = {
    -9, -8, -7, -6, -5, -4, -3, -2, -1,
    7, 8, 9, 77, 88, 89, 90, 97, 98, 99,
    997, 998, 999, 9997, 9998, 9999,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build code-compatible profiles from CEPS Stata tables."
    )
    parser.add_argument("--wave1-student", required=True)
    parser.add_argument("--wave2-student", required=True)
    parser.add_argument("--wave2-teacher")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-students", type=int, default=0)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--include-outcomes",
        action="store_true",
        help="Include attention outcomes for offline validation only.",
    )
    return parser.parse_args()


def clean_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").replace(
        list(MISSING_CODES), np.nan
    )


def safe_mean(frame: pd.DataFrame, columns: list[str]) -> pd.Series:
    available = [column for column in columns if column in frame.columns]
    if not available:
        return pd.Series(np.nan, index=frame.index)
    return frame[available].mean(axis=1)


def minmax(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    finite = values[np.isfinite(values)]
    if finite.empty:
        return pd.Series(np.nan, index=values.index)
    low, high = float(finite.min()), float(finite.max())
    if math.isclose(low, high):
        return pd.Series(0.5, index=values.index)
    return (values - low) / (high - low)


def tier(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "medium"
    if not math.isfinite(number):
        return "medium"
    if number < 0.33:
        return "low"
    if number > 0.67:
        return "high"
    return "medium"


def economic_label(value: Any) -> str:
    labels = {
        1: "very constrained",
        2: "constrained",
        3: "average",
        4: "comfortable",
        5: "very comfortable",
    }
    try:
        return labels.get(int(value), "unknown")
    except (TypeError, ValueError):
        return "unknown"


def migration_label(value: Any) -> str:
    labels = {
        1: "local non-migrant",
        2: "interprovincial migrant",
        3: "intraprovincial migrant",
    }
    try:
        return labels.get(int(value), "unknown")
    except (TypeError, ValueError):
        return "unknown"


def parent_education_label(father: Any, mother: Any) -> str:
    values = []
    for value in (father, mother):
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            values.append(number)
    if not values:
        return "unknown"
    maximum = max(values)
    if maximum <= 2:
        return "low"
    if maximum <= 4:
        return "medium"
    return "high"


def pseudonym(identifier: Any, prefix: str) -> str:
    digest = hashlib.sha256(str(identifier).encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{digest}"


def read_stata(path: Path, requested: list[str] | None = None) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(path)
    frame = pd.read_stata(path, convert_categoricals=False)
    if requested is None:
        return frame
    available = [column for column in requested if column in frame.columns]
    return frame[available].copy()


def build_profiles(
    wave1_path: Path,
    wave2_path: Path,
    teacher_path: Path | None,
    max_students: int,
    seed: int,
    include_outcomes: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[tuple[str, str, str]]]:
    wave2_all = read_stata(wave2_path)
    communication_columns = sorted(
        column for column in wave2_all if column.lower().startswith("w2a21")
    )
    outcome_columns = [
        "w2b0504", "w2b0505", "w2b0506",
        "w2b0507", "w2b0508", "w2b0509", "w2b0603",
    ]
    wave1 = read_stata(
        wave1_path,
        [
            "ids", "clsids", "schids", "steco_5c", "stfedu", "stmedu",
            "stdchn", "stdmat", "stmigrant", "a1204",
        ],
    )
    selected_wave2 = [
        "ids", "clsids", "schids", "w2d0305",
        *communication_columns,
        *(outcome_columns if include_outcomes else []),
    ]
    wave2 = wave2_all[
        [column for column in selected_wave2 if column in wave2_all]
    ].copy()
    if "ids" not in wave1 or "ids" not in wave2:
        raise ValueError("Both student tables must contain the `ids` column.")

    frame = wave2.merge(
        wave1, on="ids", how="left", validate="one_to_one", suffixes=("", "_w1")
    )
    for column in frame:
        if column not in {"ids", "clsids", "schids"}:
            frame[column] = clean_numeric(frame[column])

    frame["ability"] = safe_mean(frame, ["stdmat", "stdchn"])
    frame["communication"] = safe_mean(
        frame, ["a1204", "w2d0305", *communication_columns]
    )
    frame["ability_scaled"] = minmax(frame["ability"])
    frame["communication_scaled"] = minmax(frame["communication"])
    frame["socioeconomic_scaled"] = (
        minmax(frame["steco_5c"])
        if "steco_5c" in frame
        else pd.Series(np.nan, index=frame.index)
    )
    if max_students > 0 and len(frame) > max_students:
        frame = frame.sample(max_students, random_state=seed).reset_index(drop=True)

    classes = sorted(
        {
            str(value)
            for value in frame.get("clsids", pd.Series(dtype=object)).dropna()
        }
    )
    school_by_class: dict[str, str] = {}
    if "clsids" in frame and "schids" in frame:
        for _, row in frame[["clsids", "schids"]].dropna().iterrows():
            school_by_class[str(row["clsids"])] = str(row["schids"])

    teacher_id_by_class: dict[str, str] = {}
    if teacher_path and teacher_path.is_file():
        teacher_frame = read_stata(teacher_path)
        if "clsids" in teacher_frame:
            identifier = "tchids" if "tchids" in teacher_frame else None
            for class_id, group in teacher_frame.dropna(
                subset=["clsids"]
            ).groupby("clsids"):
                raw_id = group.iloc[0][identifier] if identifier else class_id
                teacher_id_by_class[str(class_id)] = pseudonym(raw_id, "T")

    teachers = []
    for class_id in classes:
        teacher_id = teacher_id_by_class.setdefault(
            class_id, pseudonym(class_id, "T")
        )
        teachers.append(
            {
                "id": teacher_id,
                "agent_type": "TeacherAgent",
                "name": teacher_id,
                "class_id": class_id,
                "school_id": school_by_class.get(class_id, ""),
                "clsids": class_id,
                "schids": school_by_class.get(class_id, ""),
                "policy_mode": "merit",
                "question_difficulty_default": 0.5,
            }
        )

    students = []
    relationships = []
    for _, row in frame.iterrows():
        raw_id = row["ids"]
        student_id = pseudonym(raw_id, "S")
        class_id = str(row.get("clsids", ""))
        school_id = str(row.get("schids", ""))
        ability = tier(row.get("ability_scaled"))
        communication = tier(row.get("communication_scaled"))
        socioeconomic = tier(row.get("socioeconomic_scaled"))
        public_profile = {
            "family_economy": economic_label(row.get("steco_5c")),
            "parent_education": parent_education_label(
                row.get("stfedu"), row.get("stmedu")
            ),
            "migration_status": migration_label(row.get("stmigrant")),
            "academic_level": ability,
            "communication_level": communication,
            "socioeconomic_level": socioeconomic,
        }
        observed_outcomes: dict[str, Any] = {}
        if include_outcomes:
            for column in outcome_columns:
                value = row.get(column)
                observed_outcomes[column] = (
                    None if pd.isna(value) else float(value)
                )
        students.append(
            {
                "id": student_id,
                "agent_type": "StudentAgent",
                "name": student_id,
                "class_id": class_id,
                "school_id": school_id,
                "profile_public": public_profile,
                "prompt_summary": (
                    f"Academic performance is {ability}; communication is "
                    f"{communication}; socioeconomic background is "
                    f"{socioeconomic}; migration status is "
                    f"{public_profile['migration_status']}."
                ),
                "observed_outcomes": observed_outcomes,
            }
        )
        relationships.append(
            (
                teacher_id_by_class.get(
                    class_id, pseudonym(class_id or "unknown", "T")
                ),
                student_id,
                "bidirectional",
            )
        )
    return students, teachers, relationships


def write_outputs(
    output_dir: Path,
    students: list[dict[str, Any]],
    teachers: list[dict[str, Any]],
    relationships: list[tuple[str, str, str]],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, records in (
        ("StudentAgent.json", students),
        ("TeacherAgent.json", teachers),
    ):
        with (output_dir / name).open("w", encoding="utf-8") as handle:
            json.dump(records, handle, ensure_ascii=False, indent=2)
    with (output_dir / "Relationship.csv").open("w", encoding="utf-8") as handle:
        handle.write("source_id,target_id,direction\n")
        for source, target, direction in relationships:
            handle.write(f"{source},{target},{direction}\n")
    stats = {
        "students": len(students),
        "teachers": len(teachers),
        "relationships": len(relationships),
    }
    with (output_dir / "build_stats.json").open("w", encoding="utf-8") as handle:
        json.dump(stats, handle, indent=2)


def main() -> None:
    args = parse_args()
    students, teachers, relationships = build_profiles(
        wave1_path=Path(args.wave1_student).expanduser().resolve(),
        wave2_path=Path(args.wave2_student).expanduser().resolve(),
        teacher_path=(
            Path(args.wave2_teacher).expanduser().resolve()
            if args.wave2_teacher
            else None
        ),
        max_students=args.max_students,
        seed=args.seed,
        include_outcomes=args.include_outcomes,
    )
    output_dir = Path(args.output_dir).expanduser().resolve()
    write_outputs(output_dir, students, teachers, relationships)
    print(
        json.dumps(
            {
                "students": len(students),
                "teachers": len(teachers),
                "relationships": len(relationships),
                "output_dir": str(output_dir),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
