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
    safe_number,
    safe_list,
    safe_avg,
    log_metric_error
)

def average_credibility_score(data: Dict[str, Any]) -> Any:
    """
    Metric: average_credibility_score
    Description: Measures the average credibility score of information as evaluated by Ordinary Users. This reflects the overall perception of information reliability in the system.
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
            log_metric_error("average_credibility_score", ValueError("Invalid data input"), {"data": data})
            return 0.0
        logger.info(f"credibility_score data: {data}")
        credibility_scores = safe_list(safe_get(data, "credibility_score", []))

        # Calculate the average credibility score
        average_score = safe_avg(credibility_scores, 0.0)

        # Return result for line visualization type
        return average_score

    except Exception as e:
        log_metric_error("average_credibility_score", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return 0.0

from typing import Dict, Any
from onesim.monitor.utils import (
    safe_get,
    safe_list,
    safe_count,
    log_metric_error
)

def opinion_expression_rate(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculates the opinion expression rate for Ordinary Users.
    This is the proportion of users who have expressed an opinion.

    Args:
        data (Dict[str, Any]): Input data containing agent variables.

    Returns:
        Dict[str, float]: A dictionary suitable for pie chart visualization
                          with "active" and "inactive" categories.
    """
    try:
        # Validate input data
        if not data or not isinstance(data, dict):
            log_metric_error("opinion_expression_rate", ValueError("Invalid data input"), {"data": data})
            return {"active": 0, "inactive": 1}

        # Retrieve the list of expressed_opinion values for Ordinary Users
        expressed_opinions = safe_list(safe_get(data, "expressed_opinion", []))

        logger.info(f"expressed_opinions: {expressed_opinions}")
        # Count the number of active users (non-None and non-empty string opinions)
        active_users_count = safe_count(expressed_opinions, predicate=lambda x: isinstance(x, str) and x.strip() != "")

        # Total number of users
        total_users_count = len(expressed_opinions)

        # Handle division by zero (no users)
        if total_users_count == 0:
            return {"active": 0, "inactive": 1}

        # Calculate active and inactive proportions
        active_rate = active_users_count / total_users_count
        inactive_rate = 1 - active_rate

        # Return results in a format suitable for pie chart visualization
        return {"active": active_rate, "inactive": inactive_rate}

    except Exception as e:
        # Log any unexpected errors
        log_metric_error("opinion_expression_rate", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {"active": 0, "inactive": 1}

from typing import Dict, Any
from onesim.monitor.utils import (
    safe_get, safe_list, safe_count, safe_avg, log_metric_error
)

def fact_checking_rumor_detection_rate(data: Dict[str, Any]) -> Dict[str, int]:
    """
    Measures the average number of rumors detected by Fact-Check Organizations.
    Returns a dictionary mapping organization categories to average rumor counts.
    """
    try:
        # Validate input data
        if not data or not isinstance(data, dict):
            log_metric_error("fact_checking_rumor_detection_rate", ValueError("Invalid data input"), {"data": data})
            return {}

        detected_rumors = safe_list(safe_get(data, "detected_rumors", []))
        rumor_counts = []
        for rumor in detected_rumors:
            valid_rumor_count = safe_count(rumor, predicate=lambda x: x is not None)
            rumor_counts.append(valid_rumor_count)

        # Calculate average rumor detection rate
        average_rumor_count = safe_avg(rumor_counts, default=0)

        # Return result in bar chart format (dictionary mapping categories to values)
        return {"FactCheckOrganizations": average_rumor_count}

    except Exception as e:
        # Log any unexpected errors
        log_metric_error("fact_checking_rumor_detection_rate", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {"FactCheckOrganizations": 0}

# Metric function registry
METRIC_FUNCTIONS = {
    'average_credibility_score': average_credibility_score,
    'opinion_expression_rate': opinion_expression_rate,
    'fact_checking_rumor_detection_rate': fact_checking_rumor_detection_rate,
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

