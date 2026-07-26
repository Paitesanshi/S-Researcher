# -*- coding: utf-8 -*-
"""
Auto-generated monitoring metric calculation module
"""

from typing import Dict, Any, List, Optional, Union, Callable
import math
from loguru import logger
from onesim.monitor.utils import (
    safe_get,
    safe_number,
    safe_list,
    safe_sum,
    safe_avg,
    safe_max,
    safe_min,
    safe_count,
    log_metric_error,
)


from typing import Dict, Any
from onesim.monitor.utils import safe_list, safe_avg, log_metric_error

def Average_Cooperation_Willingness(data: Dict[str, Any]) -> Any:
    """
    Metric: Average Cooperation Willingness
    Description: Measures the average willingness of individuals to cooperate in collective actions.
    Visualization type: line
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        - line: Return a scalar value
        - bar/pie: Return a dictionary mapping categories to values
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Check if required variables exist and validate input data
        if not data or not isinstance(data, dict):
            log_metric_error("Average Cooperation Willingness", ValueError("Invalid data input"), {"data": data})
            return 0.0
        
        # Extract cooperation_willingness values from individuals
        cooperation_willingness_values = safe_list(data.get("cooperation_willingness", []))

        # Calculate the average cooperation willingness, excluding None values
        average_willingness = safe_avg(cooperation_willingness_values, default=0.0)

        # Return the result as a single value for line visualization type
        return average_willingness
    
    except Exception as e:
        log_metric_error("Average Cooperation Willingness", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return 0.0

def Collective_Action_Success_Rate(data: Dict[str, Any]) -> Any:
    """
    Metric: Collective Action Success Rate
    Description: Indicates the proportion of time the collective action is successful.
    Visualization type: line
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        - line: Return a scalar value
        - bar/pie: Return a dictionary mapping categories to values
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    from onesim.monitor.utils import safe_get, safe_list, safe_count, log_metric_error

    try:
        # Validate input data
        if not data or not isinstance(data, dict):
            log_metric_error("Collective Action Success Rate", ValueError("Invalid data input"), {"data": data})
            return 0.0

        # Retrieve collective_success variable, ensuring it's a list
        collective_success_list = safe_list(safe_get(data, "collective_success", []))

        # Count the number of successful actions (True values)
        success_count = safe_count(collective_success_list, predicate=lambda x: x is True)

        # Count the number of valid observations (non-None values)
        total_count = safe_count(collective_success_list, predicate=lambda x: x is not None)

        # Calculate the success rate
        if total_count == 0:
            return 0.0  # Avoid division by zero

        success_rate = success_count / total_count
        return success_rate

    except Exception as e:
        log_metric_error("Collective Action Success Rate", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return 0.0

def Total_Group_Benefit(data: Dict[str, Any]) -> Any:
    """
    Metric: Total Group Benefit
    Description: Represents the total benefit achieved by the group from individual cooperation.
    Visualization type: bar
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        - line: Return a scalar value
        - bar/pie: Return a dictionary mapping categories to values
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    from onesim.monitor.utils import safe_get, safe_number, log_metric_error

    try:
        # Validate input data
        if not data or not isinstance(data, dict):
            log_metric_error("Total Group Benefit", ValueError("Invalid data input"), {"data": data})
            return {}

        # Retrieve group_benefit from the environment variables
        group_benefit = safe_get(data, "group_benefit")
        group_benefit = safe_number(group_benefit, default=0.0)

        # Prepare result for bar visualization
        result = {"Total Group Benefit": group_benefit}

        return result

    except Exception as e:
        log_metric_error("Total Group Benefit", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

# Metric function registry
METRIC_FUNCTIONS = {
    'Average_Cooperation_Willingness': Average_Cooperation_Willingness,
    'Collective_Action_Success_Rate': Collective_Action_Success_Rate,
    'Total_Group_Benefit': Total_Group_Benefit,
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


def test_metric_function(function_name: str, test_data: Dict[str, Any]) -> Any:
    """
    
    Args:
        function_name: Function name
        
    Returns:
    """
    func = get_metric_function(function_name)
    if func is None:
        raise ValueError(f"Metric function not found: {function_name}")
    
    try:
        result = func(test_data)
        print(f"Metric {function_name} result: {result}")
        return result
    except Exception as e:
        log_metric_error(function_name, e, {"test_data": test_data})
        raise


def generate_test_data() -> Dict[str, Any]:
    """
    
    Returns:
    """
    return {
        "total_steps": 100,
        "current_time": 3600,
        "resource_pool": 1000,
        
        "agent_health": [100, 90, 85, 70, None, 60],
        "agent_resources": [50, 40, 30, 20, 10, None],
        "agent_age": [10, 20, 30, 40, 50, 60],
        
        "empty_list": [],
        "none_value": None,
        "zero_value": 0,
        
        "should_be_list_but_single": 42,
        "invalid_number": "not_a_number",
    }


def test_all_metrics(test_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    
    Args:
        
    Returns:
    """
    if test_data is None:
        test_data = generate_test_data()
        
    results = {}
    for func_name, func in METRIC_FUNCTIONS.items():
        try:
            result = func(test_data)
            results[func_name] = result
        except Exception as e:
            results[func_name] = f"ERROR: {str(e)}"
            log_metric_error(func_name, e, {"test_data": test_data})
    
    return results


if __name__ == "__main__":
    
    test_data = generate_test_data()
    
    results = test_all_metrics(test_data)
    
    for func_name, result in results.items():
        print(f"{func_name}: {result}")
