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

def Government_Policy_Efficiency(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Government Policy Efficiency
    Description: Measures the average efficiency of government policy execution.
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
        # Access the efficiency_metrics list from the Government agent
        efficiency_metrics = safe_list(safe_get(data, 'efficiency_metrics', []))

        # Calculate the average efficiency, handling empty lists and None values
        average_efficiency = safe_avg(efficiency_metrics)

        # Return the result as a dictionary suitable for line visualization
        # return {'Government Policy Efficiency': average_efficiency}
        return average_efficiency

    except Exception as e:
        log_metric_error("Government Policy Efficiency", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {'Government Policy Efficiency': 0.0}

from typing import Dict, Any
from onesim.monitor.utils import (
    safe_get, safe_list, safe_avg, log_metric_error
)

def Citizen_Policy_Acceptance(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Citizen Policy Acceptance
    Description: Represents the average level of citizen acceptance towards government policies.
    Visualization type: line
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        line: Return a dictionary mapping series names to values
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Validate the input data
        if not data or not isinstance(data, dict):
            log_metric_error("Citizen Policy Acceptance", ValueError("Invalid data input"), {"data": data})
            return {"average_acceptance": 0}

        # Access the 'acceptance_level' variable from the Citizens agent
        acceptance_levels = safe_list(safe_get(data, 'satisfaction_level', []))

        # Calculate the average acceptance level, excluding None values
        average_acceptance = safe_avg(acceptance_levels, default=0)

        # Return result in appropriate format for line visualization
        # return {"average_acceptance": average_acceptance}
        return average_acceptance

    except Exception as e:
        log_metric_error("Citizen Policy Acceptance", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {"average_acceptance": 0}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, log_metric_error

def Policy_Strength_Adjustment_Reasons(data: Dict[str, Any]) -> Dict[str, int]:
    """
    Metric: Policy Strength Adjustment Reasons
    Description: Analyzes the reasons for adjustments in policy strength by the government.
    Visualization type: bar

    Args:
        data: Dictionary containing all variables; agent variables are lists

    Returns:
        Return a dictionary mapping categories to values

    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Initialize the result dictionary
        result = {}

        # Retrieve the adjustment reasons list from the data dictionary
        adjustment_reasons = safe_list(safe_get(data, 'adjustment_reason'))

        # Validate the adjustment_reasons list
        if not adjustment_reasons:
            log_metric_error("Policy Strength Adjustment Reasons", ValueError("Adjustment reasons list is empty or missing"), {"data": data})
            return result
        
        # Count occurrences of each adjustment reason
        for reason in adjustment_reasons:
            if reason is None or not isinstance(reason, str):
                # Log error for invalid reason type
                log_metric_error("Policy Strength Adjustment Reasons", ValueError("Invalid adjustment reason type"), {"reason": reason})
                continue
            
            # Increment the count for the reason in the result dictionary
            if reason in result:
                result[reason] += 1
            else:
                result[reason] = 1

        return result

    except Exception as e:
        log_metric_error("Policy Strength Adjustment Reasons", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

# Metric function registry
METRIC_FUNCTIONS = {
    'Government_Policy_Efficiency': Government_Policy_Efficiency,
    'Citizen_Policy_Acceptance': Citizen_Policy_Acceptance,
    'Policy_Strength_Adjustment_Reasons': Policy_Strength_Adjustment_Reasons,
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
