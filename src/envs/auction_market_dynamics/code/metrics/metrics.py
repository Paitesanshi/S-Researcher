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
    safe_get,
    safe_list,
    safe_avg,
    log_metric_error
)

def Bidding_Decision_Over_Time(data: Dict[str, Any]) -> Any:
    """
    Metric: Average Buyer Private Value
    Description: Measures the average private valuation of buyers participating in auctions, providing insights into the perceived value of auctioned items.
    Visualization type: bar
    
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
            log_metric_error("Bidding Decision Over Time", ValueError("Invalid data input"), {"data": data})
            return {}

        # Retrieve the list of private values from Buyer agents



        # Filter out None values
        # valid_private_values = [value for value in private_values if value is not None]
        cnt = 0
        for x in data['bidding_decision']:
            cnt += x


        # Calculate the average private value
        # average_value = safe_avg(data['private_value'], default=0)

        # Return result in the format required for a bar visualization
        return {"Bidding Decision Over Time": cnt}

    except Exception as e:
        log_metric_error("Bidding Decision Over Time", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, safe_avg, log_metric_error

def Average_Seller_Reserve_Price(data: Dict[str, Any]) -> Any:
    """
    Metric: Seller Reserve Price vs Production Cost
    Description: Compares the average reserve price set by sellers to their production costs, indicating pricing strategies and potential profit margins.
    Visualization type: bar
    
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
            log_metric_error("Average Seller Reserve Price", ValueError("Invalid data input"), {"data": data})
            return {}

        # Retrieve and safely convert seller reserve price decisions and production costs
        reserve_price_decisions = safe_list(safe_get(data, "reserve_price_decision", []))
        # production_costs = safe_list(safe_get(data, "production_cost", []))

        # Calculate average reserve price and production cost, ignore None values
        avg_reserve_price = safe_avg([rp for rp in reserve_price_decisions if rp is not None])
        # avg_production_cost = safe_avg([pc for pc in production_costs if pc is not None])

        # Prepare result for bar visualization
        result = {
            "Average Reserve Price": avg_reserve_price,
            # "Average Production Cost": avg_production_cost
        }

        return result
    except Exception as e:
        log_metric_error("Average Seller Reserve Price", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

# Metric function registry
METRIC_FUNCTIONS = {
    'Bidding_Decision_Over_Time': Bidding_Decision_Over_Time,
    'Average_Seller_Reserve_Price': Average_Seller_Reserve_Price,
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

