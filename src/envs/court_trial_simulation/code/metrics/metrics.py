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
from onesim.monitor.utils import safe_get, safe_list, safe_count, log_metric_error

def Prosecution_Decision_Rate(data: Dict[str, Any]) -> Any:
    """
    Metric: Prosecution Decision Rate
    Description: Measures the proportion of prosecution decisions made by prosecutors, indicating the level of activity and decision-making within the prosecution process.
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
        # Validate the input data
        if not data or not isinstance(data, dict):
            log_metric_error("Prosecution Decision Rate", ValueError("Invalid data input"), {"data": data})
            return {}

        # Retrieve prosecution decisions safely
        prosecution_decisions = safe_list(safe_get(data, "prosecution_decision", []))
        logger.info(f"prosecution_decisions: {prosecution_decisions}")
        # Handle None values by treating them as 'undecided'
        valid_decisions = [decision if decision is not None else 'undecided' for decision in prosecution_decisions]

        # Count the number of 'proceed' decisions
        prosecute_count = safe_count(valid_decisions, lambda x: x == 'proceed')

        # Count the total number of decisions excluding 'undecided'
        total_decisions = safe_count(valid_decisions, lambda x: x != 'undecided')

        # Calculate the prosecution decision rate
        if total_decisions == 0:
            prosecution_decision_rate = 0.0
        else:
            prosecution_decision_rate = prosecute_count / total_decisions

        # Return the result in appropriate format for pie visualization
        return {"Prosecute": prosecution_decision_rate, "Other": 1 - prosecution_decision_rate}
    
    except Exception as e:
        log_metric_error("Prosecution Decision Rate", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, safe_avg, log_metric_error

def Average_Evidence_Quality(data: Dict[str, Any]) -> Any:
    """
    Metric: Average Evidence Quality
    Description: Calculates the average quality of evidence available to prosecutors, reflecting the strength of the case being built.
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
        # Check if required variables exist and validate input data
        if not data or not isinstance(data, dict):
            log_metric_error("Average Evidence Quality", ValueError("Invalid data input"), {"data": data})
            return {}

        # Retrieve the list of evidence quality values for Prosecutors
        evidence_quality_values = safe_list(safe_get(data, "evidence_quality", []))

        # Filter out None values and ensure all elements are numbers
        valid_evidence_quality = [float(value) for value in evidence_quality_values]

        # Calculate the average using the safe_avg utility function
        average_quality = safe_avg(valid_evidence_quality, default=0.0)

        # Return the result in the appropriate format for a bar chart
        return {"Average Evidence Quality": average_quality}

    except Exception as e:
        log_metric_error("Average Evidence Quality", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

from typing import Dict, Any
from onesim.monitor.utils import (
    safe_get,
    safe_list,
    safe_count,
    log_metric_error
)

def Jury_Verdict_Distribution(data: Dict[str, Any]) -> Any:
    """
    Metric: Jury Verdict Distribution
    Description: Shows the distribution of verdicts made by juries, providing insight into the outcomes of trials and the decision-making tendencies of juries.
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
        # Ensure the data is a valid dictionary
        if not data or not isinstance(data, dict):
            log_metric_error("Jury Verdict Distribution", ValueError("Invalid data input"), {"data": data})
            return {}

        # Extract the list of verdicts from the data
        verdicts = safe_list(safe_get(data, "verdict", []))

        # Initialize a dictionary to count occurrences of each verdict
        verdict_distribution = {}

        # Count each verdict, excluding None values
        for verdict in verdicts:
            if verdict is not None and isinstance(verdict, str):
                if verdict not in verdict_distribution:
                    verdict_distribution[verdict] = 0
                verdict_distribution[verdict] += 1

        # If the verdict distribution is empty, return zero counts for common verdict types
        if not verdict_distribution:
            verdict_distribution = {"guilty": 0, "not guilty": 0, "undecided": 0}

        return verdict_distribution

    except Exception as e:
        log_metric_error("Jury Verdict Distribution", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

# Metric function registry
METRIC_FUNCTIONS = {
    'Prosecution_Decision_Rate': Prosecution_Decision_Rate,
    'Average_Evidence_Quality': Average_Evidence_Quality,
    'Jury_Verdict_Distribution': Jury_Verdict_Distribution,
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


