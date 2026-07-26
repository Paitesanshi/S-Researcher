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

def Community_Mobilization_Status(data: Dict[str, Any]) -> Dict[str, int]:
    """
    Metric: Community Mobilization Status
    Description: Tracks the proportion of community leaders actively engaged in mobilization activities.
    Visualization type: pie
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Access the mobilization_status list from the data
        mobilization_status_list = safe_list(safe_get(data, 'mobilization_status', []))

        # Define predicates for counting active and inactive statuses
        def is_active(status):
            return status == 'active'

        def is_inactive(status):
            return status is None or status != 'active'

        # Count active and inactive statuses
        active_count = safe_count(mobilization_status_list, is_active)
        inactive_count = safe_count(mobilization_status_list, is_inactive)

        # Return the result as a dictionary suitable for a pie chart
        result = {
            'Active': active_count,
            'Inactive': inactive_count
        }
        return result

    except Exception as e:
        log_metric_error("Community Mobilization Status", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {'Active': 0, 'Inactive': 0}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, safe_count, log_metric_error

def Community_Participation_Rate(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Community Participation Rate
    Description: Measures the average participation rate of community members in health mobilization activities.
    Visualization type: bar

    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Access the participation_status list safely
        participation_status_list = safe_list(safe_get(data, 'participation_status', []))
        
        if not participation_status_list:
            # If the list is empty, log an error and return a default value
            log_metric_error("Community Participation Rate", ValueError("Participation status list is empty or not found"), {"data": data})
            return {"Participation Rate": 0.0}
        
        # Count the number of 'participating' statuses
        participating_count = safe_count(participation_status_list, lambda status: status == 'participating')
        
        # Calculate the participation rate
        total_count = len(participation_status_list)
        
        if total_count == 0:
            # Handle division by zero if the list is empty
            log_metric_error("Community Participation Rate", ZeroDivisionError("Total count of members is zero"), {"data": data})
            return {"Participation Rate": 0.0}
        
        participation_rate = (participating_count / total_count) * 100
        
        return {"Participation Rate": participation_rate}
    
    except Exception as e:
        # Log any unexpected errors
        log_metric_error("Community Participation Rate", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {"Participation Rate": 0.0}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, log_metric_error

def Guidance_Provision_Status(data: Dict[str, Any]) -> Dict[str, int]:
    """
    Metric: Guidance Provision Status
    Description: Analyzes the distribution of guidance statuses provided by public health experts.
    Visualization type: bar
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Accessing the guidance_status variable from PublicHealthExpert
        guidance_status_list = safe_list(safe_get(data, 'guidance_status', []))

        # Initialize a dictionary to count occurrences of each status
        status_count = {}

        # Iterate over the list and count each unique status
        for status in guidance_status_list:
            # Handle None values by categorizing them under 'None'
            if status is None:
                status = 'None'
            
            # Count occurrences of each status
            if status in status_count:
                status_count[status] += 1
            else:
                status_count[status] = 1

        return status_count

    except Exception as e:
        log_metric_error("Guidance Provision Status", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

# Metric function registry
METRIC_FUNCTIONS = {
    'Community_Mobilization_Status': Community_Mobilization_Status,
    'Community_Participation_Rate': Community_Participation_Rate,
    'Guidance_Provision_Status': Guidance_Provision_Status,
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
