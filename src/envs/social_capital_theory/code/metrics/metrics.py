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
from onesim.monitor.utils import safe_get, safe_number, safe_list, safe_avg, log_metric_error

def Average_Social_Capital(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Average Social Capital
    Description: Measures the average social capital of all individual agents in the system.
    Visualization type: line
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Access the social capital values from the data dictionary
        social_capital_values = safe_list(safe_get(data, 'social_capital_value', []))
        
        # Filter out invalid values (None or non-numeric) and convert to float
        valid_values = [safe_number(value) for value in social_capital_values if value is not None]
        
        # Calculate average social capital using safe_avg
        average_social_capital = safe_avg(valid_values, default=0)
        
        # Return result in the format suitable for line visualization
        return {'Average Social Capital': average_social_capital}
    
    except Exception as e:
        # Log any errors encountered during the calculation
        log_metric_error("Average Social Capital", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {'Average Social Capital': 0}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, safe_count, log_metric_error

def Cooperation_Rate(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Cooperation Rate
    Description: Represents the proportion of individual agents that have a positive cooperation potential.
    Visualization type: pie
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        Return a dictionary mapping categories to values
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Access cooperation_potential data
        cooperation_potential_list = safe_list(safe_get(data, 'cooperation_potential', []))
        
        # Validate the list and count the number of True values
        if not cooperation_potential_list:
            return {"cooperative": 0.0, "non_cooperative": 0.0}

        # Count the number of True values
        true_count = safe_count(cooperation_potential_list, predicate=lambda x: x is True)
        
        # Count valid entries (not None)
        valid_entries_count = safe_count(cooperation_potential_list, predicate=lambda x: x is not None)

        # Handle division by zero scenario
        if valid_entries_count == 0:
            return {"cooperative": 0.0, "non_cooperative": 0.0}

        # Calculate proportions
        cooperative_rate = true_count / valid_entries_count
        non_cooperative_rate = 1 - cooperative_rate

        # Return result as a dictionary for pie chart visualization
        return {"cooperative": cooperative_rate, "non_cooperative": non_cooperative_rate}
    
    except Exception as e:
        log_metric_error("Cooperation Rate", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {"cooperative": 0.0, "non_cooperative": 0.0}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, log_metric_error

def Resource_Access_Decisions(data: Dict[str, Any]) -> Dict[str, int]:
    """
    Metric: Resource Access Decisions
    Description: Tracks the number of agents making each type of decision regarding resource access.
    Visualization type: bar
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Access the 'decision' variable from IndividualAgent
        decision_list = safe_list(safe_get(data, 'decision', []))
        
        # Initialize the result dictionary
        decision_counts = {}

        # Iterate over the decision list and count occurrences of each decision type
        for decision in decision_list:
            if decision is None or not isinstance(decision, str):
                # Skip None values and invalid types
                continue
            if decision not in decision_counts:
                decision_counts[decision] = 0
            decision_counts[decision] += 1

        return decision_counts

    except Exception as e:
        log_metric_error("Resource Access Decisions", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

# Metric function registry
METRIC_FUNCTIONS = {
    'Average_Social_Capital': Average_Social_Capital,
    'Cooperation_Rate': Cooperation_Rate,
    'Resource_Access_Decisions': Resource_Access_Decisions,
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
