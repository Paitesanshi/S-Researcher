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

def average_worker_productivity(data: Dict[str, Any]) -> Any:
    """
    Metric: average_worker_productivity
    Description: Measures the average productivity level of all Worker Agents.
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
        # logger.info(f"Average Worker Productivity data: {data}")
        # Check if required variables exist and validate input data
        if not data or not isinstance(data, dict):
            log_metric_error("average_worker_productivity", ValueError("Invalid data input"), {"data": data})
            return 0

        # Retrieve productivity_level data from WorkerAgent
        productivity_levels = safe_get(data, "productivity_level", default=None)

        # Ensure productivity_levels is a list
        productivity_levels = safe_list(productivity_levels)

        # Calculate the average productivity level, handling None values
        average_productivity = safe_avg(productivity_levels, default=0)

        # Return result as a single value for line visualization
        return average_productivity

    except Exception as e:
        log_metric_error("average_worker_productivity", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return 0

def leadership_attention_impact(data: Dict[str, Any]) -> Any:
    """
    Metric: leadership_attention_impact
    Description: Assesses the correlation between leadership attention levels and worker productivity.
    Visualization type: bar
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        - line: Return a scalar value
        - bar/pie: Return a dictionary mapping categories to values
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    from onesim.monitor.utils import (
        safe_get, safe_number, safe_list, safe_sum, safe_avg, log_metric_error
    )
    
    try:
        # Validate input data
        if not data or not isinstance(data, dict):
            log_metric_error("leadership_attention_impact", ValueError("Invalid data input"), {"data": data})
            return {}

        # Retrieve and validate leadership_attention_level and productivity_level
        leadership_attention_levels = safe_list(safe_get(data, "leadership_attention_level"))
        productivity_levels = safe_list(safe_get(data, "productivity_level"))

        # Check if lists are of equal length
        if len(leadership_attention_levels) != len(productivity_levels):
            log_metric_error("leadership_attention_impact", ValueError("Mismatched list lengths"), {
                "leadership_attention_levels_length": len(leadership_attention_levels),
                "productivity_levels_length": len(productivity_levels)
            })
            return {}

        # Categorize leadership attention levels
        categories = {"low": [], "medium": [], "high": []}
        for attention, productivity in zip(leadership_attention_levels, productivity_levels):
            if attention is None or productivity is None:
                continue  # Skip None values

            attention = safe_number(attention)
            productivity = safe_number(productivity)

            if attention < 3:
                categories["low"].append(productivity)
            elif attention < 7:
                categories["medium"].append(productivity)
            else:
                categories["high"].append(productivity)

        # Calculate average productivity for each category
        result = {}
        for category, values in categories.items():
            if values:
                result[category] = safe_avg(values)
            else:
                result[category] = 0.0  # Default to 0 if no values

        return result

    except Exception as e:
        log_metric_error("leadership_attention_impact", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

from typing import Dict, Any
from collections import Counter
from onesim.monitor.utils import (
    safe_get, safe_list, log_metric_error
)

def emotional_state_distribution(data: Dict[str, Any]) -> Any:
    """
    Metric: emotional_state_distribution
    Description: Shows the distribution of emotional states among Worker Agents.
    Visualization type: pie
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        - line: Return a scalar value
        - bar/pie: Return a dictionary mapping categories to values
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Validate input data
        if not data or not isinstance(data, dict):
            log_metric_error("emotional_state_distribution", ValueError("Invalid data input"), {"data": data})
            return {}

        # Extract WorkerAgent emotional states
        emotional_states = safe_list(safe_get(data, "emotional_state", []))

        # Filter out None values
        valid_emotional_states = [state for state in emotional_states if state is not None]

        # If no valid emotional states, return empty distribution
        if not valid_emotional_states:
            return {}

        # Count occurrences of each emotional state
        state_counts = Counter(valid_emotional_states)

        # Calculate total count for proportional values
        total_count = sum(state_counts.values())

        # Handle division by zero
        if total_count == 0:
            return {}

        # Calculate proportional values
        emotional_state_distribution = {state: count / total_count for state, count in state_counts.items()}

        return emotional_state_distribution

    except Exception as e:
        log_metric_error("emotional_state_distribution", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

# Metric function registry
METRIC_FUNCTIONS = {
    'average_worker_productivity': average_worker_productivity,
    'leadership_attention_impact': leadership_attention_impact,
    'emotional_state_distribution': emotional_state_distribution,
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
