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

def Average_Cultural_Capital_Level(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Average Cultural Capital Level
    Description: This metric measures the average level of cultural capital among all IndividualAgents.
    Visualization type: line
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        Return a dictionary mapping series names to values
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Access the cultural capital level data
        cultural_capital_values = safe_list(safe_get(data, 'cultural_capital_level', []))
        
        # Filter out None values and ensure all values are numbers
        valid_values = [safe_number(value, None) for value in cultural_capital_values if value is not None]
        
        # Calculate the average using safe_avg
        average_cultural_capital_level = safe_avg(valid_values, default=0.0)
        
        # Return result in the format appropriate for a line chart
        return {'Average Cultural Capital Level': average_cultural_capital_level}
    
    except Exception as e:
        log_metric_error("Average Cultural Capital Level", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {'Average Cultural Capital Level': 0.0}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, safe_count, log_metric_error

def Education_Decision_Rate(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Education Decision Rate
    Description: This metric measures the proportion of IndividualAgents who have decided to pursue education.
    Visualization type: pie
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Access the education_decision list from the data dictionary
        education_decision_list = safe_list(safe_get(data, 'education_decision', []))

        # Count the number of True values in the education_decision list
        true_count = safe_count(education_decision_list, lambda x: x is True)

        # Count the number of non-None values in the education_decision list
        non_none_count = safe_count(education_decision_list, lambda x: x is not None)

        # Calculate the proportion
        if non_none_count == 0:
            proportion = 0.0
        else:
            proportion = true_count / non_none_count

        # Return result formatted for pie chart visualization
        return {"Education Pursued": proportion, "Not Pursued": 1 - proportion}

    except Exception as e:
        log_metric_error("Education Decision Rate", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {"Education Pursued": 0.0, "Not Pursued": 1.0}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, log_metric_error

def Job_Search_Status_Distribution(data: Dict[str, Any]) -> Dict[str, int]:
    """
    Metric: Job Search Status Distribution
    Description: This metric shows the distribution of IndividualAgents across different job search statuses.
    Visualization type: bar
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        Return a dictionary mapping categories to values
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Access the job_search_status variable from the data dictionary
        job_search_status_list = safe_list(safe_get(data, 'job_search_status', []))
        
        # Initialize a dictionary to count occurrences of each status
        status_distribution = {}

        # Iterate over the list and count occurrences of each status
        for status in job_search_status_list:
            if status is not None and isinstance(status, str):
                if status in status_distribution:
                    status_distribution[status] += 1
                else:
                    status_distribution[status] = 1

        return status_distribution

    except Exception as e:
        log_metric_error("Job Search Status Distribution", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

# Metric function registry
METRIC_FUNCTIONS = {
    'Average_Cultural_Capital_Level': Average_Cultural_Capital_Level,
    'Education_Decision_Rate': Education_Decision_Rate,
    'Job_Search_Status_Distribution': Job_Search_Status_Distribution,
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
