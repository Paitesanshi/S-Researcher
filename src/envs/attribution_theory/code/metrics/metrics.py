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
from onesim.monitor.utils import safe_get, safe_list, safe_count, log_metric_error

def Attribution_Type_Distribution(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate the Attribution Type Distribution metric.
    Description: Proportion of internal vs external attributions made by Participant A.
    Visualization Type: pie

    Args:
        data: A dictionary containing all variables collected by the monitor.

    Returns:
        A dictionary where keys are attribution types ('internal', 'external') and values are their proportions.
    """
    try:
        # Attempt to retrieve the attribution_type list from the data dictionary
        attribution_type_list = safe_list(safe_get(data, 'attribution_type', []))

        # Filter out None values from the list
        # valid_attributions = [attr for attr in attribution_type_list if attr is not None]


        results = {}
        for x in attribution_type_list:
            if x not in results.keys():
                results[x] = 1
            else:
                results[x] += 1
        
        return results

        # # Handle empty list scenario
        # if not valid_attributions:
        #     return {}

        # # Count occurrences of each attribution type
        # internal_count = safe_count(valid_attributions, lambda x: x == 'internal')
        # external_count = safe_count(valid_attributions, lambda x: x == 'external')

        # # Calculate total valid attributions
        # total_valid_attributions = internal_count + external_count

        # # Handle division by zero scenario
        # if total_valid_attributions == 0:
        #     return {}

        # # Calculate proportions
        # internal_proportion = internal_count / total_valid_attributions
        # external_proportion = external_count / total_valid_attributions

        # # Return the result as a dictionary suitable for pie chart visualization
        # return {
        #     'internal': internal_proportion,
        #     'external': external_proportion
    #     # }

    except Exception as e:
        log_metric_error("Attribution Type Distribution", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, safe_count, log_metric_error

def Bias_Detection_Frequency(data: Dict[str, Any]) -> Dict[str, int]:
    """
    Metric: Bias Detection Frequency
    Description: Frequency of bias detection by Feedbacker C over time.
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
        # Validate input data
        if not data or not isinstance(data, dict):
            log_metric_error("Bias Detection Frequency", ValueError("Invalid data input"), {"data": data})
            return {"default": 0}

        # Access the bias_detected variable from FeedbackerC
        bias_detected_list = safe_list(safe_get(data, 'bias_detected', []))

        # Count the number of times bias is detected, treating None as 'no bias detected'
        bias_count = safe_count(bias_detected_list, lambda x: x is True)

        # Return result in the format suitable for line visualization
        result = {"Bias Detection Frequency": bias_count}
        return result

    except Exception as e:
        log_metric_error("Bias Detection Frequency", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {"default": 0}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, log_metric_error

def Behavior_Type_Analysis(data: Dict[str, Any]) -> Dict[str, int]:
    """
    Metric: Behavior Type Analysis
    Description: Distribution of different behavior types exhibited by Participant B.
    Visualization type: bar

    Args:
        data: Dictionary containing all variables; agent variables are lists

    Returns:
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Access the 'behavior_type' list for Participant B
        behavior_types = safe_list(safe_get(data, 'behavior_type', []))

        # Initialize an empty dictionary to store the count of each behavior type
        behavior_count = {}

        # Iterate over the list and count occurrences of each behavior type
        for behavior in behavior_types:
            if behavior is not None and isinstance(behavior, str):
                if behavior in behavior_count:
                    behavior_count[behavior] += 1
                else:
                    behavior_count[behavior] = 1

        return behavior_count

    except Exception as e:
        # Log any exceptions that occur during processing
        log_metric_error("Behavior Type Analysis", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

# Metric function registry
METRIC_FUNCTIONS = {
    'Attribution_Type_Distribution': Attribution_Type_Distribution,
    'Bias_Detection_Frequency': Bias_Detection_Frequency,
    'Behavior_Type_Analysis': Behavior_Type_Analysis,
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
