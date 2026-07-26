# -*- coding: utf-8 -*-
"""
Auto-generated monitoring metric calculation module
"""

from typing import Dict, Any, List, Optional, Union, Callable
import math
from loguru import logger
from onesim.monitor.utils import (
    safe_get, safe_number, safe_list, safe_sum, 
    safe_avg, safe_max, safe_min, safe_count, log_metric_error
)


from typing import Dict, Any
from onesim.monitor.utils import (
    safe_get,
    safe_list,
    log_metric_error
)

def Employee_Feedback_Sentiment(data: Dict[str, Any]) -> Any:
    """
    Metric: Employee Feedback Sentiment
    Description: Measures the overall sentiment of employee feedback regarding organizational changes.
    Visualization type: pie
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        Return a format appropriate for the visualization type:
        - line: Return a scalar value
        - bar/pie: Return a dictionary mapping categories to values
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Validate input
        if not data or not isinstance(data, dict):
            log_metric_error("Employee Feedback Sentiment", ValueError("Invalid data input"), {"data": data})
            return {}

        # Extract and validate employee feedback
        feedback_list = safe_list(safe_get(data, "feedback", []))

        logger.info(f"feedback_list: {feedback_list}")
        
        if not feedback_list:
            log_metric_error("Employee Feedback Sentiment", ValueError("Feedback list is empty or invalid"), {"feedback": feedback_list})
            return {}

        # Initialize sentiment counters
        sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}

        # Dummy sentiment analysis function
        def analyze_sentiment(feedback):
            # Placeholder for actual sentiment analysis logic
            if "positive" in feedback.lower() or "appreciate" in feedback.lower() or "well" in feedback.lower():
                return "positive"
            elif "negative" in feedback.lower() or "dislike" in feedback.lower() or "bad" in feedback.lower():
                return "negative"
            else:
                return "neutral"

        # Process each feedback entry
        for feedback in feedback_list:
            if feedback is None or not isinstance(feedback, str) or feedback.strip() == "":
                continue  # Skip invalid feedback entries

            sentiment = analyze_sentiment(feedback)
            if sentiment in sentiment_counts:
                sentiment_counts[sentiment] += 1

        # Calculate total feedback count
        total_feedback = sum(sentiment_counts.values())
        if total_feedback == 0:
            log_metric_error("Employee Feedback Sentiment", ValueError("No valid feedback entries processed"), {"feedback": feedback_list})
            return {}

        # Calculate proportions
        sentiment_proportions = {key: count / total_feedback for key, count in sentiment_counts.items()}

        return sentiment_proportions

    except Exception as e:
        log_metric_error("Employee Feedback Sentiment", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, safe_count, log_metric_error

def Change_Goals_Completion_Rate(data: Dict[str, Any]) -> Any:
    """
    Metric: Change Goals Completion Rate
    Description: Tracks the percentage of change goals set by LeaderAgents that have been successfully reported as completed.
    Visualization type: bar
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        Return a format appropriate for the visualization type:
        - line: Return a scalar value
        - bar/pie: Return a dictionary mapping categories to values
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Ensure the data is a valid dictionary
        if not data or not isinstance(data, dict):
            log_metric_error("Change Goals Completion Rate", ValueError("Invalid data input"), {"data": data})
            return {}

        # Retrieve change goals and final reports safely
        change_goals_list = safe_list(safe_get(data, "change_goals", []))
        final_report_list = safe_list(safe_get(data, "final_report", []))

        # Calculate the number of goals and completed goals
        total_goals = safe_count(change_goals_list)
        completed_goals = safe_count(final_report_list, predicate=lambda x: x in change_goals_list)

        # Handle division by zero scenario
        if total_goals == 0:
            completion_rate = 0.0
        else:
            completion_rate = (completed_goals / total_goals) * 100

        # Return result as a dictionary suitable for bar visualization
        return {"Change Goals Completion Rate": completion_rate}
    except Exception as e:
        log_metric_error("Change Goals Completion Rate", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

from typing import Dict, Any
from onesim.monitor.utils import (
    safe_get, safe_list, safe_avg, log_metric_error
)

def Manager_Execution_Effectiveness(data: Dict[str, Any]) -> Any:
    """
    Metric: Manager Execution Effectiveness
    Description: Evaluates how effectively managers are executing change strategies by comparing planned strategies to execution status.
    Visualization type: line
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        Return a format appropriate for the visualization type:
        - line: Return a scalar value
        - bar/pie: Return a dictionary mapping categories to values
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Validate input data
        if not data or not isinstance(data, dict):
            log_metric_error("Manager Execution Effectiveness", ValueError("Invalid data input"), {"data": data})
            return 0

        # Extract ManagerAgent variables
        execution_status_list = safe_list(safe_get(data, "execution_status", []))
        adjusted_strategy_list = safe_list(safe_get(data, "adjusted_strategy", []))

        # Ensure both lists are of the same length
        if len(execution_status_list) != len(adjusted_strategy_list):
            log_metric_error(
                "Manager Execution Effectiveness",
                ValueError("Mismatched list lengths"),
                {"execution_status_list_length": len(execution_status_list), "adjusted_strategy_list_length": len(adjusted_strategy_list)}
            )
            return 0

        # Calculate effectiveness for each ManagerAgent
        effectiveness_scores = []
        for execution_status, adjusted_strategy in zip(execution_status_list, adjusted_strategy_list):
            try:
                # Check both values for validity
                if execution_status is None or adjusted_strategy is None:
                    effectiveness_scores.append(0)
                elif isinstance(execution_status, str) and isinstance(adjusted_strategy, str):
                    # Evaluate match (exact match or similarity can be customized here)
                    effectiveness_scores.append(1 if execution_status == adjusted_strategy else 0)
                else:
                    effectiveness_scores.append(0)
            except Exception as e:
                log_metric_error(
                    "Manager Execution Effectiveness",
                    e,
                    {"execution_status": execution_status, "adjusted_strategy": adjusted_strategy}
                )
                effectiveness_scores.append(0)

        # Aggregate effectiveness scores (average for line chart)
        overall_effectiveness = safe_avg(effectiveness_scores)

        # Return result for line visualization
        return overall_effectiveness

    except Exception as e:
        log_metric_error("Manager Execution Effectiveness", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return 0

# Metric function registry
METRIC_FUNCTIONS = {
    'Employee_Feedback_Sentiment': Employee_Feedback_Sentiment,
    'Change_Goals_Completion_Rate': Change_Goals_Completion_Rate,
    'Manager_Execution_Effectiveness': Manager_Execution_Effectiveness,
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

