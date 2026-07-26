# -*- coding: utf-8 -*-
"""
Teacher Attention Allocation Metrics
"""

from typing import Dict, Any, List, Optional, Callable
from loguru import logger
from onesim.monitor.utils import (
    safe_get, safe_number, safe_list, safe_sum,
    safe_avg, log_metric_error
)


def attention_gini_coefficient(data: Dict[str, Any]) -> Dict[str, Any]:
    """


    Args:

    Returns:
        {"gini_coefficient": float, "timestamp": list}
    """
    try:
        attention_data = safe_list(safe_get(data, 'attention_distribution', []))

        if not attention_data:
            log_metric_error("attention_gini_coefficient", ValueError("Empty attention_distribution"))
            return {"gini_coefficient": [], "timestamp": []}

        all_records = []
        for teacher_records in attention_data:
            if isinstance(teacher_records, list):
                all_records.extend(teacher_records[-1])

        if not all_records:
            return {"gini_coefficient": [], "timestamp": []}

        student_attention = {}
        for record in all_records:
            if not isinstance(record, dict):
                continue
            student_id = record.get('selected_student_id', '')
            attention = safe_number(record.get('attention_value', 0))
            if student_id:
                student_attention[student_id] = student_attention.get(student_id, 0) + attention

        if not student_attention:
            return {"gini_coefficient": [], "timestamp": []}

        attention_values = sorted(student_attention.values())
        n = len(attention_values)

        if n == 0 or sum(attention_values) == 0:
            gini = 0.0
        else:
            cumsum = sum((i + 1) * x for i, x in enumerate(attention_values))
            total = sum(attention_values)
            gini = (2 * cumsum) / (n * total) - (n + 1) / n

        return {
            "gini_coefficient": [gini],
            "total_students": [n],
            "total_attention": [sum(attention_values)]
        }

    except Exception as e:
        log_metric_error("attention_gini_coefficient", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {"gini_coefficient": [], "timestamp": []}


def student_attention_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """

    Args:

    Returns:
        {"student_id": [total_attention], "selection_count": [count], ...}
    """
    try:
        attention_data = safe_list(safe_get(data, 'attention_distribution', []))

        if not attention_data:
            log_metric_error("student_attention_summary", ValueError("Empty attention_distribution"))
            return {}

        all_records = []
        for teacher_records in attention_data:
            if isinstance(teacher_records, list):
                all_records.extend(teacher_records)

        student_stats = {}  # {student_id: {"attention": float, "count": int}}

        for record in all_records:
            if not isinstance(record, dict):
                continue

            student_id = record.get('selected_student_id', '')
            attention = safe_number(record.get('attention_value', 0))

            if student_id:
                if student_id not in student_stats:
                    student_stats[student_id] = {"attention": 0, "count": 0}
                student_stats[student_id]["attention"] += attention
                student_stats[student_id]["count"] += 1

        if not student_stats:
            return {}

        result = {
            "labels": [],
            "total_attention": [],
            "selection_count": [],
            "avg_attention_per_selection": []
        }

        for student_id, stats in sorted(student_stats.items()):
            result["labels"].append(student_id)
            result["total_attention"].append(stats["attention"])
            result["selection_count"].append(stats["count"])
            avg = stats["attention"] / stats["count"] if stats["count"] > 0 else 0
            result["avg_attention_per_selection"].append(avg)

        return result

    except Exception as e:
        log_metric_error("student_attention_summary", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}


def hand_raising_effectiveness(data: Dict[str, Any]) -> Dict[str, Any]:
    """


    Args:

    Returns:
        {"raised_selected_rate": float, "not_raised_selected_rate": float, ...}
    """
    try:
        attention_data = safe_list(safe_get(data, 'attention_distribution', []))
        raise_hand_data = safe_list(safe_get(data, 'raise_hand_history', []))

        if not attention_data or not raise_hand_data:
            log_metric_error("hand_raising_effectiveness", ValueError("Missing required data"))
            return {}

        all_selections = []
        for teacher_records in attention_data:
            if isinstance(teacher_records, list):
                all_selections.extend(teacher_records)

        all_raise_hands = []
        for student_records in raise_hand_data:
            if isinstance(student_records, list):
                all_raise_hands.extend(student_records)

        if not all_selections or not all_raise_hands:
            return {}


        raised_selected = 0
        raised_total = 0
        not_raised_selected = 0
        not_raised_total = 0


        for record in all_raise_hands:
            if not isinstance(record, dict):
                continue

            raised = record.get('raised', False)

            if raised:
                raised_total += 1
            else:
                not_raised_total += 1

        selected_students = set()
        for selection in all_selections:
            if isinstance(selection, dict):
                student_id = selection.get('selected_student_id', '')
                if student_id:
                    selected_students.add(student_id)


        result = {
            "raised_hand_total": raised_total,
            "not_raised_total": not_raised_total,
            "total_selections": len(all_selections),
            "unique_students_selected": len(selected_students)
        }

        return result

    except Exception as e:
        log_metric_error("hand_raising_effectiveness", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}


def question_difficulty_impact(data: Dict[str, Any]) -> Dict[str, Any]:
    """


    Args:

    Returns:
        {"difficulty_levels": [0.3, 0.5, 0.8], "avg_selections": [2.1, 3.5, 1.8], ...}
    """
    try:
        attention_data = safe_list(safe_get(data, 'attention_distribution', []))

        if not attention_data:
            log_metric_error("question_difficulty_impact", ValueError("Empty attention_distribution"))
            return {}

        all_records = []
        for teacher_records in attention_data:
            if isinstance(teacher_records, list):
                all_records.extend(teacher_records)

        if not all_records:
            return {}

        difficulty_stats = {}  # {difficulty: {"total_selected": int, "rounds": int}}

        for record in all_records:
            if not isinstance(record, dict):
                continue

            difficulty = safe_number(record.get('difficulty', 0.5))
            total_selected = safe_number(record.get('total_selected', 1))

            difficulty_key = round(difficulty, 1)

            if difficulty_key not in difficulty_stats:
                difficulty_stats[difficulty_key] = {"total_selected": 0, "rounds": 0}

            difficulty_stats[difficulty_key]["total_selected"] += total_selected
            difficulty_stats[difficulty_key]["rounds"] += 1

        if not difficulty_stats:
            return {}

        result = {
            "difficulty_levels": [],
            "avg_students_per_round": [],
            "total_rounds": []
        }

        for difficulty in sorted(difficulty_stats.keys()):
            stats = difficulty_stats[difficulty]
            avg = stats["total_selected"] / stats["rounds"] if stats["rounds"] > 0 else 0

            result["difficulty_levels"].append(difficulty)
            result["avg_students_per_round"].append(avg)
            result["total_rounds"].append(stats["rounds"])

        return result

    except Exception as e:
        log_metric_error("question_difficulty_impact", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}


# Metric function registry
METRIC_FUNCTIONS = {
    'attention_gini_coefficient': attention_gini_coefficient,
    'student_attention_summary': student_attention_summary,
    'hand_raising_effectiveness': hand_raising_effectiveness,
    'question_difficulty_impact': question_difficulty_impact,
}


def get_metric_function(function_name: str) -> Optional[Callable]:
    """
    Return the metric function by name

    Args:
        function_name: Function name

    Returns:
        Metric function or None
    """
    return METRIC_FUNCTIONS.get(function_name)
