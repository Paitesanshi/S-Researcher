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

def Average_Loan_Amount_by_Economic_Condition(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Average Loan Amount by Economic Condition
    Description: Measures the average loan amount requested by customers under different economic conditions.
    Visualization type: bar
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
    """
    try:
        # Accessing the economic conditions from the environment
        economic_conditions = safe_get(data, 'economic_conditions')
        if economic_conditions is None:
            log_metric_error("Average Loan Amount by Economic Condition", ValueError("Missing economic_conditions variable"))
            return {}

        # Accessing the loan amounts from CustomerAgent
        loan_amounts = safe_list(safe_get(data, 'loan_amount', []))

        # Group and calculate average loan amounts by economic condition
        condition_to_loan_amounts = {}
        
        # Assuming each loan amount corresponds to the current economic condition
        for loan in loan_amounts:
            if loan is not None and isinstance(loan, (int, float)):
                if economic_conditions not in condition_to_loan_amounts:
                    condition_to_loan_amounts[economic_conditions] = []
                condition_to_loan_amounts[economic_conditions].append(loan)

        # Calculate average loan amount for each economic condition
        result = {}
        for condition, amounts in condition_to_loan_amounts.items():
            if amounts:
                result[condition] = safe_avg(amounts)
            else:
                result[condition] = 0  # Default value if no loans

        return result

    except Exception as e:
        log_metric_error("Average Loan Amount by Economic Condition", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

from typing import Dict, Any
from onesim.monitor.utils import (
    safe_get, safe_number, safe_list, safe_avg, log_metric_error
)

def Bank_Reserve_Utilization(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Bank Reserve Utilization
    Description: Monitors the ratio of actual reserves to reserve requirements across all banks, indicating overall reserve sufficiency.
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
        # Access the reserve requirement from the environment
        reserve_requirement = safe_number(safe_get(data, 'reserve_requirement'))
        if reserve_requirement is None or reserve_requirement == 0:
            log_metric_error("Bank Reserve Utilization", ValueError("Invalid or missing reserve requirement"))
            return {"Bank Reserve Utilization": 0}

        # Access the list of reserve levels from BankAgent
        reserve_levels = safe_list(safe_get(data, 'reserve_level', []))
        
        # Filter out None values in reserve levels
        valid_reserve_levels = [safe_number(level) for level in reserve_levels if level is not None]

        # Calculate the ratios of reserve levels to reserve requirement
        ratios = [
            level / reserve_requirement
            for level in valid_reserve_levels
            if reserve_requirement != 0
        ]

        # Calculate the average ratio
        average_ratio = safe_avg(ratios)

        # Return the result as a dictionary for line visualization
        return {"Bank Reserve Utilization": average_ratio}
    
    except Exception as e:
        log_metric_error("Bank Reserve Utilization", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {"Bank Reserve Utilization": 0}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, safe_count, log_metric_error

def Loan_Approval_Rate(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Loan Approval Rate
    Description: Tracks the percentage of loan requests approved by banks, providing insight into lending behavior.
    Visualization type: pie
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Access the decision_status list from BankAgent
        decision_status_list = safe_list(safe_get(data, 'decision_status', []))

        # Count the number of approved and rejected statuses
        approved_count = safe_count(decision_status_list, lambda x: x == 'approved')
        rejected_count = safe_count(decision_status_list, lambda x: x == 'rejected')

        # Calculate the total valid decisions (excluding None values)
        total_decisions = approved_count + rejected_count

        # Handle division by zero scenario
        if total_decisions == 0:
            return {"Approved": 0.0, "Rejected": 0.0}

        # Calculate the approval rate
        approval_rate = (approved_count / total_decisions) * 100
        rejection_rate = (rejected_count / total_decisions) * 100

        # Return the result in the format suitable for pie visualization
        return {"Approved": approval_rate, "Rejected": rejection_rate}

    except Exception as e:
        log_metric_error("Loan Approval Rate", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {"Approved": 0.0, "Rejected": 0.0}

# Metric function registry
METRIC_FUNCTIONS = {
    'Average_Loan_Amount_by_Economic_Condition': Average_Loan_Amount_by_Economic_Condition,
    'Bank_Reserve_Utilization': Bank_Reserve_Utilization,
    'Loan_Approval_Rate': Loan_Approval_Rate,
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
