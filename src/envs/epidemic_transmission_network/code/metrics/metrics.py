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
    safe_get, safe_list, safe_count, log_metric_error
)

def Infection_Rate_Over_Time(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Infection Rate Over Time
    Description: Measures the percentage of the population that is infected over time, providing insights into the spread of the disease and the effectiveness of interventions.
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
        # Access the health_status list from the data dictionary
        health_status_list = safe_list(safe_get(data, 'health_status', []))
        
        # Count total number of individuals
        total_individuals = safe_count(health_status_list)
        
        if total_individuals == 0:
            # Handle division by zero scenario
            return {"infection_rate": 0.0}
        
        # Count the number of infected individuals
        number_of_infected_individuals = safe_count(
            health_status_list, 
            predicate=lambda status: status == 'infected'
        )
        
        # Calculate infection rate
        infection_rate = (number_of_infected_individuals / total_individuals) * 100
        
        # Return the result as a dictionary suitable for line visualization
        return {"infection_rate": infection_rate}
    
    except Exception as e:
        log_metric_error("Infection Rate Over Time", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {"infection_rate": 0.0}

from typing import Dict, Any

def Resource_Utilization_by_Healthcare_Facilities(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Resource Utilization by Healthcare Facilities
    Description: Measures the utilization of healthcare facilities in terms of occupancy and staff levels, providing insights into the strain on the healthcare system.
    Visualization type: bar
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        Return a format appropriate for the visualization type:
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Check if required variables exist and validate input data
        if not data or not isinstance(data, dict):
            log_metric_error("Resource Utilization by Healthcare Facilities", ValueError("Invalid data input"), {"data": data})
            return {}

        current_occupancy = safe_list(safe_get(data, 'current_occupancy', []))
        staff_level = safe_list(safe_get(data, 'staff_level', []))

        # Ensure both lists have the same length
        if len(current_occupancy) != len(staff_level):
            log_metric_error("Resource Utilization by Healthcare Facilities", ValueError("Lists of current_occupancy and staff_level do not match in length"))
            return {}

        # Define the capacity (constant value)
        capacity = 100  # Example capacity value, should be defined based on actual data or provided as a parameter

        # Initialize result dictionary
        result = {}

        # Calculate utilization for each facility
        for i in range(len(current_occupancy)):
            if current_occupancy[i] is None or staff_level[i] is None:
                continue
            if current_occupancy[i] == 0:
                utilization = 0
            else:
                utilization = current_occupancy[i] / capacity
            result[i] = utilization

        return result
    except Exception as e:
        log_metric_error("Resource Utilization by Healthcare Facilities", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, safe_avg, safe_sum, log_metric_error

def Behavioral_Compliance_by_Demographic_Groups(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Behavioral Compliance by Demographic Groups
    Description: Measures the compliance tendency of individuals across different demographic groups, providing insights into how different segments of the population respond to interventions and information dissemination.
    Visualization type: pie
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Check if required variables exist and validate input data
        if not data or not isinstance(data, dict):
            log_metric_error("Behavioral Compliance by Demographic Groups", ValueError("Invalid data input"), {"data": data})
            return {}

        compliance_tendency = safe_list(safe_get(data, 'compliance_tendency', []))
        demographic_group = safe_list(safe_get(data, 'demographic_group', []))

        if len(compliance_tendency) != len(demographic_group):
            log_metric_error("Behavioral Compliance by Demographic Groups", ValueError("Unequal length of compliance_tendency and demographic_group"), {"compliance_tendency": compliance_tendency, "demographic_group": demographic_group})
            return {}

        if not compliance_tendency or not demographic_group:
            log_metric_error("Behavioral Compliance by Demographic Groups", ValueError("Empty compliance_tendency or demographic_group"), {"compliance_tendency": compliance_tendency, "demographic_group": demographic_group})
            return {}

        compliance_by_group = {}
        for i in range(len(compliance_tendency)):
            if compliance_tendency[i] is None or demographic_group[i] is None:
                continue

            compliance_tendency_val = safe_number(compliance_tendency[i])
            demographic_group_val = demographic_group[i]

            if demographic_group_val not in compliance_by_group:
                compliance_by_group[demographic_group_val] = []

            compliance_by_group[demographic_group_val].append(compliance_tendency_val)

        result = {group: safe_avg(values) for group, values in compliance_by_group.items()}
        return result
    except Exception as e:
        log_metric_error("Behavioral Compliance by Demographic Groups", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

# Metric function registry
METRIC_FUNCTIONS = {
    'Infection_Rate_Over_Time': Infection_Rate_Over_Time,
    'Resource_Utilization_by_Healthcare_Facilities': Resource_Utilization_by_Healthcare_Facilities,
    'Behavioral_Compliance_by_Demographic_Groups': Behavioral_Compliance_by_Demographic_Groups,
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
