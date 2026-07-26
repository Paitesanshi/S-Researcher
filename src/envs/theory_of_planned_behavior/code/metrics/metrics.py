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

def Average_Behavioral_Intentions(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Average Behavioral Intentions
    Description: Measures the average behavioral intentions across all CognitiveAgents, providing insight into the overall inclination towards certain behaviors in the system.
    Visualization type: line
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Access the 'behavioral_intentions' variable from CognitiveAgent
        behavioral_intentions = safe_list(safe_get(data, 'behavioral_intentions', []))
        
        # Filter out None values from the list
        filtered_intentions = [intent for intent in behavioral_intentions if intent is not None]
        
        # Calculate the average using the safe_avg utility function
        average_intention = None
        if filtered_intentions:
            average_intention = safe_avg(filtered_intentions, default=None)
        
        # Return the result in the appropriate format for line visualization
        return {'Average Behavioral Intentions': average_intention or 0}
    
    except Exception as e:
        log_metric_error("Average Behavioral Intentions", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {'Average Behavioral Intentions': 0}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_number, safe_list, safe_avg, log_metric_error

def Resource_Availability_vs__Social_Norms_Impact(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate the metric: Resource Availability vs. Social Norms Impact
    Description: Compares the average resource availability with the average social norms score to understand how environmental resources and social pressures are balancing each other.
    Visualization Type: bar
    
    Args:
        data: Dictionary containing all variables collected by the monitor, note agent variables are in list form
        
    Returns:
        Dictionary where keys are categories and values are measurements for bar visualization
        
    Note:
        This function handles various exceptional cases including None values, empty lists, and type errors
    """
    try:
        # Access 'resource_availability' from the environment
        resource_availability = safe_number(safe_get(data, 'resource_availability'), default=None)
        
        # Access 'social_norms_score' from SocialNormAgent
        social_norms_scores = safe_list(safe_get(data, 'social_norms_score', []))
        
        # Calculate average social norms score, ignoring None values
        social_norms_avg = safe_avg([score for score in social_norms_scores if score is not None], default=None)

        # Check for None values and handle accordingly
        if resource_availability is None:
            log_metric_error("Resource Availability vs. Social Norms Impact", ValueError("Missing 'resource_availability' value"), {"data": data})
            return {"Resource Availability": 0, "Social Norms Impact": social_norms_avg if social_norms_avg is not None else 0}

        if social_norms_avg is None:
            log_metric_error("Resource Availability vs. Social Norms Impact", ValueError("Missing 'social_norms_score' values or all are None"), {"data": data})
            return {"Resource Availability": resource_availability, "Social Norms Impact": 0}

        # Prepare result dictionary for bar visualization
        result = {
            "Resource Availability": resource_availability,
            "Social Norms Impact": social_norms_avg
        }
        return result

    except Exception as e:
        log_metric_error("Resource Availability vs. Social Norms Impact", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {"Resource Availability": 0, "Social Norms Impact": 0}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, log_metric_error

def Completion_Status_Distribution(data: Dict[str, Any]) -> Dict[str, int]:
    """
    Metric: Completion Status Distribution
    Description: Shows the distribution of completion statuses across all CognitiveAgents to assess how many agents have completed their tasks successfully.
    Visualization type: pie
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        Return a dictionary mapping categories to values
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Access completion_status list from data
        completion_status_list = safe_list(safe_get(data, 'completion_status', []))

        # Initialize a dictionary to store the counts of each status
        status_distribution = {}

        # Iterate over the completion_status_list
        for status in completion_status_list:
            if status is not None and isinstance(status, str):
                if status in status_distribution:
                    status_distribution[status] += 1
                else:
                    status_distribution[status] = 1
            else:
                # Handle None or invalid type by categorizing separately or logging error
                if None in status_distribution:
                    status_distribution[None] += 1
                else:
                    status_distribution[None] = 1

        return status_distribution

    except Exception as e:
        log_metric_error("Completion Status Distribution", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

# Metric function registry
METRIC_FUNCTIONS = {
    'Average_Behavioral_Intentions': Average_Behavioral_Intentions,
    'Resource_Availability_vs__Social_Norms_Impact': Resource_Availability_vs__Social_Norms_Impact,
    'Completion_Status_Distribution': Completion_Status_Distribution,
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
