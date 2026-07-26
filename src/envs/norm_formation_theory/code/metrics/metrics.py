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


from typing import Dict, Any, List
from onesim.monitor.utils import safe_get, safe_list, safe_avg, log_metric_error

def average_group_norm_conformity(data: Dict[str, Any]) -> Any:
    """
    Metric: average_group_norm_conformity
    Description: Measures the average level of conformity to group norms across all individual agents.
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
            log_metric_error("average_group_norm_conformity", ValueError("Invalid data input"), {"data": data})
            return 0.0
        
        # Retrieve adjusted_behavior_tendencies from IndividualAgent
        adjusted_behavior_tendencies_list = safe_get(data, "adjusted_behavior_tendencies", [])
        adjusted_behavior_tendencies_list = safe_list(adjusted_behavior_tendencies_list)

        # Check if list is empty
        if not adjusted_behavior_tendencies_list:
            log_metric_error("average_group_norm_conformity", ValueError("No adjusted_behavior_tendencies data available"), {"data_keys": list(data.keys())})
            return 0.0
        
        # Calculate average conformity for each agent
        agent_averages = []
        for tendencies in adjusted_behavior_tendencies_list:
            tendencies_list = safe_list(tendencies)
            if tendencies_list:
                agent_avg = safe_avg(tendencies_list)
                agent_averages.append(agent_avg)

        # Calculate overall average conformity
        if not agent_averages:
            log_metric_error("average_group_norm_conformity", ValueError("No valid agent averages computed"), {"adjusted_behavior_tendencies_list": adjusted_behavior_tendencies_list})
            return 0.0

        overall_average = safe_avg(agent_averages)
        return overall_average

    except Exception as e:
        log_metric_error("average_group_norm_conformity", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return 0.0

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_number, safe_list, safe_sum, safe_avg, log_metric_error

def group_pressure_distribution(data: Dict[str, Any]) -> Any:
    """
    Metric: group_pressure_distribution
    Description: Shows the distribution of group pressure experienced by individual agents, indicating how pressure is spread across different groups.
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
            log_metric_error("group_pressure_distribution", ValueError("Invalid data input"), {"data": data})
            return {}

        # Retrieve and validate group_pressure from environment variables
        group_pressure = safe_number(safe_get(data, "group_pressure", None))
        if group_pressure is None:
            log_metric_error("group_pressure_distribution", ValueError("Missing or invalid group_pressure"), {"data": data})
            return {}

        # Retrieve and validate group_id from agent variables
        group_ids = safe_list(safe_get(data, "group_id", []))
        if not group_ids:
            log_metric_error("group_pressure_distribution", ValueError("Missing or invalid group_id list"), {"data": data})
            return {}

        # Initialize a dictionary to store total pressure and count of agents per group
        group_pressure_map = {}

        # Iterate over agents and calculate total pressure and count per group
        for group_id in group_ids:
            if group_id is None:
                continue  # Skip agents with None group_id

            if group_id not in group_pressure_map:
                group_pressure_map[group_id] = {"total_pressure": 0.0, "agent_count": 0}

            group_pressure_map[group_id]["total_pressure"] += group_pressure
            group_pressure_map[group_id]["agent_count"] += 1

        # Calculate average group pressure for each group
        result = {}
        for group_id, values in group_pressure_map.items():
            agent_count = values["agent_count"]
            total_pressure = values["total_pressure"]
            if agent_count > 0:
                result[group_id] = total_pressure / agent_count
            else:
                result[group_id] = 0.0

        return result

    except Exception as e:
        log_metric_error("group_pressure_distribution", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, safe_count, log_metric_error

def average_norm_acceptance(data: Dict[str, Any]) -> Any:
    """
    Metric: norm_change_proportion
    Description: Represents the proportion of social groups that have undergone norm changes.
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
        norm_acceptance = safe_list(data.get("norm_acceptance"))
        avg_norm_acceptance = safe_avg(norm_acceptance)
        return {"average_group_norm_conformity": avg_norm_acceptance}

    except Exception as e:
        return {"average_group_norm_conformity": 0}

# Metric function registry
METRIC_FUNCTIONS = {
    'average_group_norm_conformity': average_group_norm_conformity,
    'group_pressure_distribution': group_pressure_distribution,
    'average_norm_acceptance': average_norm_acceptance,
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


