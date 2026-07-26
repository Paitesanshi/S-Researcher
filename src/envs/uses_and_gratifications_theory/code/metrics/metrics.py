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
from onesim.monitor.utils import safe_get, safe_list, safe_avg, log_metric_error

def average_satisfaction_level(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: average_satisfaction_level
    Description: Measures the average satisfaction level of AudienceAgents with the media they consume.
    Visualization type: line
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        Return a format appropriate for the visualization type:
        - line: Return a dictionary mapping series names to values
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Access the 'satisfaction_level' variable from the data
        satisfaction_levels = safe_list(safe_get(data, 'satisfaction_level', []))

        # Calculate the average satisfaction level
        average_satisfaction = safe_avg(satisfaction_levels, default=0)

        # Return the result formatted for a line visualization
        return {'average_satisfaction_level': average_satisfaction}

    except Exception as e:
        # Log any exceptions that occur during the calculation
        log_metric_error("average_satisfaction_level", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {'average_satisfaction_level': 0}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, log_metric_error

def media_type_selection_distribution(data: Dict[str, Any]) -> Dict[int, int]:
    """
    Metric: media_type_selection_distribution
    Description: Shows the distribution of selected media types by AudienceAgents.
    Visualization type: bar
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
    """
    try:
        # Access the 'selected_media' variable from AudienceAgents
        selected_media_list = safe_list(safe_get(data, 'selected_media', []))
        
        # Initialize the result dictionary
        media_distribution = {}

        # Count the occurrences of each media type ID in the selected_media list
        for media_id in selected_media_list:
            if media_id is None or not isinstance(media_id, int):
                continue  # Ignore None values and non-integer types
            if media_id in media_distribution:
                media_distribution[media_id] += 1
            else:
                media_distribution[media_id] = 1

        return media_distribution

    except Exception as e:
        log_metric_error("media_type_selection_distribution", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

from typing import Dict, Any
from onesim.monitor.utils import (
    safe_get, safe_number, safe_list, safe_sum,
    safe_avg, safe_max, safe_min, safe_count, log_metric_error
)
import numpy as np

def feedback_satisfaction_correlation(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: feedback_satisfaction_correlation
    Description: Analyzes the correlation between feedback history and satisfaction levels of AudienceAgents.
    Visualization type: line
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        Return a dictionary mapping series names to values
    """
    try:
        # Access the agent variables
        satisfaction_levels = safe_list(safe_get(data, 'satisfaction_level', []))
        feedback_histories = safe_list(safe_get(data, 'feedback_history', []))

        # Initialize the result dictionary
        correlation_results = {}

        # Check if both lists are of the same length
        if len(satisfaction_levels) != len(feedback_histories):
            log_metric_error("feedback_satisfaction_correlation", ValueError("Mismatched list lengths"), {
                "satisfaction_levels_length": len(satisfaction_levels),
                "feedback_histories_length": len(feedback_histories)
            })
            return {"default": 0}

        # Calculate correlation for each agent
        for i, (satisfaction, feedback) in enumerate(zip(satisfaction_levels, feedback_histories)):
            # Ensure both satisfaction and feedback are lists and not empty
            feedback = safe_list(feedback)
            if feedback is None or satisfaction is None or len(feedback) == 0:
                correlation_results[f"agent_{i}"] = 0  # Default correlation value
                continue

            try:
                # Convert satisfaction to a list for consistency
                satisfaction_values = [safe_number(satisfaction)]
                feedback_values = [safe_number(f) for f in feedback if f is not None]

                # Calculate correlation using numpy if possible
                if len(feedback_values) > 1:
                    correlation = np.corrcoef(satisfaction_values * len(feedback_values), feedback_values)[0, 1]
                else:
                    correlation = 0  # Not enough data to calculate correlation

                # Store the result
                correlation_results[f"agent_{i}"] = correlation
            except Exception as e:
                log_metric_error("feedback_satisfaction_correlation", e, {"agent_index": i})
                correlation_results[f"agent_{i}"] = 0  # Default correlation value in case of error

        return correlation_results

    except Exception as e:
        log_metric_error("feedback_satisfaction_correlation", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {"default": 0}

# Metric function registry
METRIC_FUNCTIONS = {
    'average_satisfaction_level': average_satisfaction_level,
    'media_type_selection_distribution': media_type_selection_distribution,
    'feedback_satisfaction_correlation': feedback_satisfaction_correlation,
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
