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
    safe_get, safe_number, safe_list, safe_sum, safe_avg, log_metric_error
)

def Average_Conformity_Tendency(data: Dict[str, Any]) -> Any:
    """
    Metric: Average Conformity Tendency
    Description: Measures the average tendency of individual agents to conform within the system, providing insight into overall conformity behavior.
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
        # Check if data is a valid dictionary
        if not data or not isinstance(data, dict):
            log_metric_error("Average Conformity Tendency", ValueError("Invalid data input"), {"data": data})
            return {}

        # Retrieve the list of conformity tendencies from IndividualAgent
        conformity_tendencies = safe_list(safe_get(data, "conformity_tendency", []))

        # Convert all values in the list to numbers, treating None as zero
        conformity_tendencies = [safe_number(value, default=0) for value in conformity_tendencies]

        # Calculate the average conformity tendency
        average_conformity_tendency = safe_avg(conformity_tendencies, default=0)

        # Prepare the result as a dictionary for bar visualization
        result = {"Average Conformity Tendency": average_conformity_tendency}

        return result
    except Exception as e:
        log_metric_error("Average Conformity Tendency", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

from typing import Dict, Any
from onesim.monitor.utils import (
    safe_get, safe_number, log_metric_error
)

def System_Social_Pressure(data: Dict[str, Any]) -> Any:
    """
    Metric: System Social Pressure
    Description: Tracks the level of social pressure in the environment, which influences agent decision-making and conformity.
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
            log_metric_error("System Social Pressure", ValueError("Invalid data input"), {"data": data})
            return 0
        
        # Extract social_pressure from environment variables
        social_pressure = safe_get(data.get("environment", {}), "social_pressure", None)
        
        # Convert social_pressure to a number, defaulting to 0 if None or invalid type
        social_pressure_value = safe_number(social_pressure, default=0)
        
        # Return the calculated social pressure value for line visualization
        return social_pressure_value

    except Exception as e:
        log_metric_error("System Social Pressure", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return 0

def Opinion_Leader_Influence_Strength_Distribution(data: Dict[str, Any]) -> Any:
    """
    Metric: Opinion Leader Influence Strength Distribution
    Description: Analyzes the distribution of influence strength among opinion leaders, indicating their potential impact on group dynamics.
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
        safe_get, safe_list, safe_sum, log_metric_error
    )

    try:
        # Validate input data
        if not isinstance(data, dict):
            log_metric_error("Opinion Leader Influence Strength Distribution", ValueError("Invalid data input"), {"data": data})
            return {}

        valid_influence_strengths = data['influence_strength']
        total_strength = safe_sum(valid_influence_strengths)

        # Calculate proportional values for pie chart
        distribution = {
            f"Leader {i+1}": strength / total_strength
            for i, strength in enumerate(valid_influence_strengths)
        }


        return distribution

    except Exception as e:
        log_metric_error("Opinion Leader Influence Strength Distribution", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

# Metric function registry
METRIC_FUNCTIONS = {
    'Average_Conformity_Tendency': Average_Conformity_Tendency,
    'System_Social_Pressure': System_Social_Pressure,
    'Opinion_Leader_Influence_Strength_Distribution': Opinion_Leader_Influence_Strength_Distribution,
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


