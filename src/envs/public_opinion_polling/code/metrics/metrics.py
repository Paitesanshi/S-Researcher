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

def Pollster_Completion_Rate(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Pollster Completion Rate
    Description: Measures the percentage of polls completed by pollsters.
    Visualization type: bar
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        Return a dictionary mapping categories to values
        - bar: {'Completed': percentage, 'Incomplete': percentage}
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Access the completion_status list from the data dictionary
        completion_status_list = safe_list(safe_get(data, 'completion_status', []))

        if not completion_status_list:
            # If the list is empty or None, log an error and return default values
            log_metric_error("Pollster Completion Rate", ValueError("completion_status list is empty or None"))
            return {'Completed': 0.0, 'Incomplete': 100.0}

        # Count the number of completed and total entries
        total_entries = safe_count(completion_status_list)
        completed_entries = safe_count(completion_status_list, lambda status: status == 'completed')

        # Calculate the percentage of completed polls
        if total_entries == 0:
            # Handle division by zero scenario
            log_metric_error("Pollster Completion Rate", ZeroDivisionError("Total entries count is zero"))
            return {'Completed': 0.0, 'Incomplete': 100.0}

        completed_percentage = (completed_entries / total_entries) * 100
        incomplete_percentage = 100 - completed_percentage

        return {'Completed': completed_percentage, 'Incomplete': incomplete_percentage}

    except Exception as e:
        log_metric_error("Pollster Completion Rate", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {'Completed': 0.0, 'Incomplete': 100.0}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, log_metric_error

def Voter_Preference_Dynamics(data: Dict[str, Any]) -> Dict[str, int]:
    """
    Metric: Voter Preference Dynamics
    Description: Tracks changes in voter preferences over time to analyze dynamic shifts.
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
        # Initialize the result dictionary for line chart visualization
        preference_counts = {}

        # Accessing the expressed_preferences list from the Voter agents
        expressed_preferences_list = safe_list(safe_get(data, 'expressed_preferences', []))

        # Iterate over the list to count occurrences of each preference
        for preferences in expressed_preferences_list:
            if preferences is None or not isinstance(preferences, list):
                continue  # Skip None or invalid types

            for preference in preferences:
                if preference is None or not isinstance(preference, str):
                    continue  # Skip None or invalid types

                if preference in preference_counts:
                    preference_counts[preference] += 1
                else:
                    preference_counts[preference] = 1

        return preference_counts

    except Exception as e:
        log_metric_error("Voter Preference Dynamics", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {"default": 0}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, log_metric_error

def Pollster_Voter_Interaction_Count(data: Dict[str, Any]) -> Dict[str, int]:
    """
    Metric: Pollster-Voter Interaction Count
    Description: Counts the number of interactions between pollsters and voters.
    Visualization type: bar
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        Return a dictionary mapping categories to values
        - bar: {'Total Interactions': count}
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Retrieve selected_voter_id lists from Pollster and Voter
        pollster_voter_ids = safe_list(safe_get(data, 'selected_voter_id'))
        voter_voter_ids = safe_list(safe_get(data, 'selected_voter_id'))

        # Validate that the lists are not None and contain valid data
        if not pollster_voter_ids or not isinstance(pollster_voter_ids, list):
            log_metric_error("Pollster-Voter Interaction Count", ValueError("Invalid or missing Pollster selected_voter_id"), {"data": data})
            pollster_voter_ids = []

        if not voter_voter_ids or not isinstance(voter_voter_ids, list):
            log_metric_error("Pollster-Voter Interaction Count", ValueError("Invalid or missing Voter selected_voter_id"), {"data": data})
            voter_voter_ids = []

        # Calculate the number of unique interactions
        try:
            # Use set intersection to find unique interactions
            unique_interactions = set(pollster_voter_ids).intersection(voter_voter_ids)
            interaction_count = len(unique_interactions)
        except Exception as e:
            log_metric_error("Pollster-Voter Interaction Count", e, {"pollster_voter_ids": pollster_voter_ids, "voter_voter_ids": voter_voter_ids})
            interaction_count = 0

        # Return the result as a dictionary suitable for bar chart visualization
        return {'Total Interactions': interaction_count}

    except Exception as e:
        log_metric_error("Pollster-Voter Interaction Count", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {'Total Interactions': 0}

# Metric function registry
METRIC_FUNCTIONS = {
    'Pollster_Completion_Rate': Pollster_Completion_Rate,
    'Voter_Preference_Dynamics': Voter_Preference_Dynamics,
    'Pollster_Voter_Interaction_Count': Pollster_Voter_Interaction_Count,
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
