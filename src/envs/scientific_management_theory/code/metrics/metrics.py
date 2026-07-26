# -*- coding: utf-8 -*-
"""
Auto-generated monitoring metric calculation module
"""

import json
from typing import Dict, Any, List, Optional, Union, Callable
import math
from loguru import logger
from onesim.monitor.utils import (
    safe_get, safe_number, safe_list, safe_sum, 
    safe_avg, safe_max, safe_min, safe_count, log_metric_error
)


def Average_Worker_Performance(data: Dict[str, Any]) -> Any:
    """
    Metric: Average Worker Performance
    Description: Measures the average performance of WorkerAgents based on their task completion and performance adjustment statuses.
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
    from onesim.monitor.utils import (
        safe_get, safe_number, safe_list, safe_sum, safe_avg, log_metric_error
    )

    try:
        # Safely retrieve the 'worker_performance' list from the data
        worker_performance_data = safe_get(data, 'worker_performance', default=None)

        # logger.info(f"Worker performance data: {worker_performance_data}")
        # Ensure the retrieved data is a list
        worker_performance_list = safe_list(worker_performance_data)

        all_performances = []
        for manager_item in worker_performance_list:
            for performance_item in manager_item:
                if performance_item['performance'] is not None and isinstance(performance_item['performance'], (int, float)):
                    all_performances.append(performance_item['performance'])

        # Calculate the average of valid performance values
        average_performance = safe_avg(all_performances, default=0)

        # Return the result in the required format for a bar visualization
        return {"Average Worker Performance": average_performance}

    except Exception as e:
        log_metric_error("Average Worker Performance", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {"Average Worker Performance": 0}

from typing import Dict, Any
from onesim.monitor.utils import (
    safe_get,
    safe_number,
    safe_list,
    safe_sum,
    safe_avg,
    safe_max,
    safe_min,
    safe_count,
    log_metric_error
)

def Task_Allocation_Effectiveness(data: Dict[str, Any]) -> Any:
    """
    Metric: Task Allocation Effectiveness
    Description: Evaluates how effectively tasks are allocated by comparing task allocation status with worker performance.
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
        # Check if required variables exist and validate input data
        if not data or not isinstance(data, dict):
            log_metric_error("Task Allocation Effectiveness", ValueError("Invalid data input"), {"data": data})
            return {"Effective": 0, "Ineffective": 0}
        
        # logger.info(f"Task Allocation Effectiveness data: {data}")
        # Retrieve the task_allocation_status and worker_performance lists
        task_allocation_status_list = safe_list(safe_get(data, "task_allocation_status", []))
        worker_performance_list = safe_list(safe_get(data, "worker_performance", []))
        
        # Validate that both lists have the same length
        if len(task_allocation_status_list) != len(worker_performance_list):
            log_metric_error("Task Allocation Effectiveness", ValueError("Mismatched list lengths"), {
                "task_allocation_status_length": len(task_allocation_status_list),
                "worker_performance_length": len(worker_performance_list)
            })
            return {"Effective": 0, "Ineffective": 0}
        
        # Define a high performance threshold
        high_performance_threshold = 75  # Example threshold
        
        # Calculate the number of successful allocations
        successful_allocations = 0
        total_allocations = 0
        
        for allocation_status, performance in zip(task_allocation_status_list, worker_performance_list):
            try:
                performance_value = safe_number(performance[0]["performance"], default=None)
                if allocation_status is not None and performance_value is not None:
                    total_allocations += 1
                    if performance_value >= high_performance_threshold:
                        successful_allocations += 1
            except Exception as e:
                log_metric_error("Task Allocation Effectiveness", e, {
                    "allocation_status": allocation_status,
                    "performance": performance
                })
                continue
        
        # Calculate the effectiveness proportion
        if total_allocations == 0:
            return {"Effective": "N/A", "Ineffective": "N/A"}
        
        effectiveness_proportion = successful_allocations / total_allocations
        
        # Return result in appropriate format for pie chart
        return {
            "Effective": effectiveness_proportion,
            "Ineffective": 1 - effectiveness_proportion
        }
    
    except Exception as e:
        log_metric_error("Task Allocation Effectiveness", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {"Effective": 0, "Ineffective": 0}

from typing import Dict, Any
from onesim.monitor.utils import (
    safe_get, safe_list, safe_count, log_metric_error
)

def Incentive_Plan_Utilization(data: Dict[str, Any]) -> Any:
    """
    Metric: Incentive Plan Utilization
    Description: Assesses how well the incentive plans are being utilized by comparing the number of incentives planned versus those applied.
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
            log_metric_error("Incentive Plan Utilization", ValueError("Invalid data input"), {"data": data})
            return 0
        
        logger.info(f"Incentive Plan Utilization data: {data}")
        # Retrieve and validate 'incentive_plan' data
        incentive_plan_data = safe_list(safe_get(data, "ManagerAgent", {}).get("profile.incentive_plan", []))
        num_incentives_planned = safe_count(incentive_plan_data)

        # Retrieve and validate 'performance_adjustment_status' data
        performance_adjustment_data = safe_list(safe_get(data, "WorkerAgent", {}).get("profile.performance_adjustment_status", []))
        num_incentives_applied = safe_count(performance_adjustment_data, lambda x: x is not None and x != '')

        # Calculate the utilization ratio
        if num_incentives_planned == 0:
            utilization_ratio = 0
        else:
            utilization_ratio = num_incentives_applied / num_incentives_planned
        
        return utilization_ratio

    except Exception as e:
        log_metric_error("Incentive Plan Utilization", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return 0

# Metric function registry
METRIC_FUNCTIONS = {
    'Average_Worker_Performance': Average_Worker_Performance,
    'Task_Allocation_Effectiveness': Task_Allocation_Effectiveness,
    'Incentive_Plan_Utilization': Incentive_Plan_Utilization,
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

