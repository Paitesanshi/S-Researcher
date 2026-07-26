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


def Media_Ideology_Bias_Distribution(data: Dict[str, Any]) -> Any:
    """
    Metric: Media Ideology Bias Distribution
    Description: Proportion of media outlets with different ideological biases to understand the media landscape's diversity.
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
    from onesim.monitor.utils import (
        safe_get, safe_list, log_metric_error
    )
    
    try:
        # Check if the data is a dictionary
        if not data or not isinstance(data, dict):
            log_metric_error("Media Ideology Bias Distribution", ValueError("Invalid data input"), {"data": data})
            return {}

        # Retrieve the media_ideology_bias list
        media_ideology_bias_list = safe_get(data, "media_ideology_bias", [])

        # Ensure it is a list
        media_ideology_bias_list = safe_list(media_ideology_bias_list)

        # Handle empty list scenario
        if not media_ideology_bias_list:
            return {}

        # Count occurrences of each ideology bias
        bias_count = {}
        for bias in media_ideology_bias_list:
            # Treat None values as 'Unknown'
            bias = bias if bias is not None else 'Unknown'
            if not isinstance(bias, str):
                log_metric_error("Media Ideology Bias Distribution", ValueError("Invalid data type in media_ideology_bias"), {"bias": bias})
                continue
            bias_count[bias] = bias_count.get(bias, 0) + 1

        # Calculate total number of biases for proportion calculation
        total_biases = sum(bias_count.values())

        # Handle division by zero scenario
        if total_biases == 0:
            return {}

        # Calculate proportion for each bias
        bias_distribution = {bias: count / total_biases for bias, count in bias_count.items()}

        return bias_distribution

    except Exception as e:
        log_metric_error("Media Ideology Bias Distribution", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

def Average_Voter_Information_Level(data: Dict[str, Any]) -> Any:
    """
    Metric: Average Voter Information Level
    Description: Average level of information among voters, indicating how informed the electorate is.
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
    from onesim.monitor.utils import (
        safe_get, safe_number, safe_list, safe_avg, log_metric_error
    )
    
    try:
        # Validate input data
        if not data or not isinstance(data, dict):
            log_metric_error("Average Voter Information Level", ValueError("Invalid data input"), {"data": data})
            return 0
        
        # Extract voter_information_level using safe_get and safe_list
        voter_information_levels = safe_list(safe_get(data, "voter_information_level", []))
        
        # Filter out invalid types and None values
        valid_information_levels = [
            safe_number(level, None) for level in voter_information_levels if isinstance(level, (int, float))
        ]
        
        # Calculate average using safe_avg, default to 0 for empty or invalid lists
        average_information_level = safe_avg(valid_information_levels, default=0)
        
        # Return the result for line visualization
        return average_information_level
    
    except Exception as e:
        log_metric_error("Average Voter Information Level", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return 0

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, safe_count, log_metric_error

def Party_Strategy_Change_Rate(data: Dict[str, Any]) -> Any:
    """
    Metric: Party Strategy Change Rate
    Description: Percentage of parties that have changed their strategy in the current cycle, indicating strategic shifts.
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
        # Validate input data
        if not data or not isinstance(data, dict):
            log_metric_error("Party Strategy Change Rate", ValueError("Invalid data input"), {"data": data})
            return {}

        # Safely extract the current_strategy and new_strategy lists
        current_strategy = safe_list(safe_get(data, "current_strategy", []))
        new_strategy = safe_list(safe_get(data, "new_strategy", []))

        # Check if both lists are of the same length
        if len(current_strategy) != len(new_strategy):
            log_metric_error("Party Strategy Change Rate", ValueError("Mismatched list lengths"), {
                "current_strategy_length": len(current_strategy),
                "new_strategy_length": len(new_strategy)
            })
            return {}

        # Count the number of strategy changes
        strategy_changes = safe_count(
            zip(current_strategy, new_strategy),
            predicate=lambda pair: pair[0] is not None and pair[1] is not None and pair[0] != pair[1]
        )

        # Count the total number of parties with valid strategies
        total_valid_parties = safe_count(
            zip(current_strategy, new_strategy),
            predicate=lambda pair: pair[0] is not None and pair[1] is not None
        )

        # Calculate the change rate
        if total_valid_parties == 0:
            change_rate = 0.0
        else:
            change_rate = (strategy_changes / total_valid_parties) * 100

        # Return the result as a dictionary for bar visualization
        return {"Party Strategy Change Rate": change_rate}

    except Exception as e:
        log_metric_error("Party Strategy Change Rate", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

# Metric function registry
METRIC_FUNCTIONS = {
    'Media_Ideology_Bias_Distribution': Media_Ideology_Bias_Distribution,
    'Average_Voter_Information_Level': Average_Voter_Information_Level,
    'Party_Strategy_Change_Rate': Party_Strategy_Change_Rate,
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

