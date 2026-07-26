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
from onesim.monitor.utils import safe_get, safe_list, safe_sum, safe_count, log_metric_error

def Innovation_Adoption_Rate(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Innovation Adoption Rate
    Description: Measures the percentage of agents who have adopted the innovation across all agent types.
    Visualization type: line

    Args:
        data: Dictionary containing all variables; agent variables are lists

    Returns:
    """
    try:
        # Access agent variables from the data dictionary
        adoption_decision = safe_list(safe_get(data, 'adoption_decision', []))
        consideration_status = safe_list(safe_get(data, 'consideration_status', []))
        broad_acceptance_evaluation = safe_list(safe_get(data, 'broad_acceptance_evaluation', []))
        adoption_status = safe_list(safe_get(data, 'adoption_status', []))

        # Calculate the total number of agents
        total_agents = len(adoption_decision) + len(consideration_status) + len(broad_acceptance_evaluation) + len(adoption_status)
        
        if total_agents == 0:
            log_metric_error("Innovation Adoption Rate", ValueError("Total agents count is zero, cannot calculate adoption rate."))
            return {"Innovation Adoption Rate": 0.0}

        # Calculate the number of adopters
        adopters_count = (safe_count(adoption_decision, lambda x: x is True) +
                          safe_count(consideration_status, lambda x: x is True) +
                          safe_count(broad_acceptance_evaluation, lambda x: x is True) +
                          safe_count(adoption_status, lambda x: x is True))

        # Calculate the innovation adoption rate
        adoption_rate = (adopters_count / total_agents) * 100

        # Return the result as a dictionary suitable for a line chart
        return {"Innovation Adoption Rate": adoption_rate}

    except Exception as e:
        log_metric_error("Innovation Adoption Rate", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {"Innovation Adoption Rate": 0.0}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, safe_count, log_metric_error

def Network_Connectivity_Impact(data: Dict[str, Any]) -> Dict[str, int]:
    """
    Calculate the Network Connectivity Impact metric.
    Description: Analyzes the influence of network connections on the spread of innovation.
    Visualization Type: bar
    
    Args:
        data: A dictionary containing all collected variables. Agent variables are lists.
        
    Returns:
        A dictionary suitable for bar chart visualization where keys are categories and values are measurements.
    """
    try:
        # Accessing the required variables using safe_get
        network_connections = safe_list(safe_get(data, 'network_connections', []))
        spread_status = safe_list(safe_get(data, 'spread_status', []))
        
        # Count the number of network connections
        num_network_connections = safe_count(network_connections)
        
        # Count the number of innovators who have successfully spread the innovation
        num_successful_spreads = safe_count(spread_status, predicate=lambda x: x is True)
        
        # Return the results as a dictionary suitable for a bar chart
        result = {
            "Network Connections": num_network_connections,
            "Successful Spreads": num_successful_spreads
        }
        return result

    except Exception as e:
        log_metric_error("Network Connectivity Impact", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {"Network Connections": 0, "Successful Spreads": 0}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_number, safe_list, safe_sum, safe_count, log_metric_error

def Relative_Advantage_vs_Adoption(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Relative Advantage vs Adoption
    Description: Compares the relative advantage of the innovation with the adoption status across agent types.
    Visualization type: pie
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Access and validate the 'relative_advantage' variable
        relative_advantage = safe_number(safe_get(data, 'relative_advantage'))
        if relative_advantage is None:
            log_metric_error("Relative Advantage vs Adoption", ValueError("Missing or invalid 'relative_advantage'"))
            return {"Adopters": 0, "Non-Adopters": 0}

        # Access and validate the 'adoption_decision' list
        adoption_decision_list = safe_list(safe_get(data, 'adoption_decision', []))
        if not adoption_decision_list:
            log_metric_error("Relative Advantage vs Adoption", ValueError("Missing or empty 'adoption_decision' list"))
            return {"Adopters": 0, "Non-Adopters": 0}

        # Count adopters and non-adopters
        adopters_count = safe_count(adoption_decision_list, lambda x: x is True)
        non_adopters_count = safe_count(adoption_decision_list, lambda x: x is False)

        # Handle division by zero scenario
        total_agents = adopters_count + non_adopters_count
        if total_agents == 0:
            log_metric_error("Relative Advantage vs Adoption", ValueError("No valid adoption data"))
            return {"Adopters": 0, "Non-Adopters": 0}

        # Calculate proportions
        adopters_proportion = adopters_count / total_agents
        non_adopters_proportion = non_adopters_count / total_agents

        # Return result in pie chart format
        return {
            "Adopters": adopters_proportion,
            "Non-Adopters": non_adopters_proportion
        }

    except Exception as e:
        log_metric_error("Relative Advantage vs Adoption", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {"Adopters": 0, "Non-Adopters": 0}

# Metric function registry
METRIC_FUNCTIONS = {
    'Innovation_Adoption_Rate': Innovation_Adoption_Rate,
    'Network_Connectivity_Impact': Network_Connectivity_Impact,
    'Relative_Advantage_vs_Adoption': Relative_Advantage_vs_Adoption,
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
