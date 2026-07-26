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

def Average_Cash_Reserves_of_Companies(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Average Cash Reserves of Companies
    Description: Measures the average cash reserves across all CompanyAgents to assess overall liquidity in the system.
    Visualization type: line
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
    """
    try:
        # Access the 'cash_reserves' variable from CompanyAgent
        cash_reserves_list = safe_list(safe_get(data, 'cash_reserves', []))
        
        # Calculate the average cash reserves excluding None values
        average_cash_reserves = safe_avg(cash_reserves_list, default=0)
        
        # Return result as a dictionary for line visualization
        return {'Average Cash Reserves': average_cash_reserves}
    
    except Exception as e:
        # Log any errors encountered during metric calculation
        log_metric_error("Average Cash Reserves of Companies", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {'Average Cash Reserves': 0}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, safe_sum, log_metric_error

def Total_Loan_Amount_Approved_by_Banks(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Total Loan Amount Approved by Banks
    Description: Tracks the total amount of loans approved by all BankAgents, indicating the level of financial support provided to companies.
    Visualization type: bar
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        Return a dictionary mapping categories to values
    """
    try:
        # Attempt to retrieve the 'approved_loan_amount' list from the data
        approved_loan_amounts = safe_list(safe_get(data, 'approved_loan_amount', []))

        # Calculate the total sum of approved loan amounts, ignoring None values
        total_approved_loans = safe_sum(approved_loan_amounts, default=0)

        # Return the result in the appropriate format for a bar chart
        return {"Total Approved Loan Amount": total_approved_loans}

    except Exception as e:
        # Log any exceptions that occur during the calculation
        log_metric_error("Total Loan Amount Approved by Banks", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {"Total Approved Loan Amount": 0}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, safe_sum, log_metric_error

def Consumer_Spending_Distribution(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Consumer Spending Distribution
    Description: Shows the distribution of spending amounts by consumers, providing insight into consumer behavior and its impact on company revenue.
    Visualization type: pie
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        Return a dictionary mapping categories to values
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Access the spending_amount list from ConsumerAgent
        spending_amounts = safe_list(safe_get(data, 'spending_amount', []))
        
        # Define spending categories
        categories = {
            'low': (0, 50),
            'medium': (50, 200),
            'high': (200, float('inf'))
        }

        # Initialize category totals
        category_totals = {category: 0 for category in categories.keys()}

        # Aggregate spending amounts into categories
        for amount in spending_amounts:
            try:
                amount = float(amount)  # Ensure the amount is a float
                if amount is not None:
                    for category, (low, high) in categories.items():
                        if low <= amount < high:
                            category_totals[category] += amount
                            break
            except (TypeError, ValueError):
                log_metric_error("Consumer Spending Distribution", ValueError("Invalid spending amount"), {"amount": amount})

        # Calculate total spending for proportion calculation
        total_spending = safe_sum(category_totals.values())

        # Calculate proportions
        if total_spending > 0:
            category_proportions = {category: total / total_spending for category, total in category_totals.items()}
        else:
            category_proportions = {category: 0 for category in categories.keys()}

        return category_proportions

    except Exception as e:
        log_metric_error("Consumer Spending Distribution", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {category: 0 for category in categories.keys()}

# Metric function registry
METRIC_FUNCTIONS = {
    'Average_Cash_Reserves_of_Companies': Average_Cash_Reserves_of_Companies,
    'Total_Loan_Amount_Approved_by_Banks': Total_Loan_Amount_Approved_by_Banks,
    'Consumer_Spending_Distribution': Consumer_Spending_Distribution,
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
