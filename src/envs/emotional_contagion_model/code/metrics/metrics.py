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

def Average_Emotional_Intensity(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Average Emotional Intensity
    Description: Measures the average intensity of emotions communicated by agents in the system.
    Visualization type: line
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        Return a dictionary mapping series names to values
    """
    try:
        # Access the 'intensity' variable from CommunicationAgent
        intensity_values = safe_list(safe_get(data, 'intensity', []))

        # Calculate average intensity using safe_avg
        average_intensity = safe_avg(intensity_values, default=0)

        # Return result in the format suitable for line visualization
        return {'Average Emotional Intensity': average_intensity}
    except Exception as e:
        log_metric_error("Average Emotional Intensity", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {'Average Emotional Intensity': 0}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, log_metric_error

def Emotional_State_Distribution(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Emotional State Distribution
    Description: Shows the proportion of agents in different emotional states to understand the emotional atmosphere of the group.
    Visualization type: pie
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Access the 'emotional_state' variable from IndividualAgent
        emotional_states = safe_list(safe_get(data, 'emotional_state', []))
        
        # Filter out None and non-string values
        valid_emotional_states = [state for state in emotional_states if isinstance(state, str) and state is not None]

        # Count occurrences of each emotional state
        state_count = {}
        for state in valid_emotional_states:
            if state in state_count:
                state_count[state] += 1
            else:
                state_count[state] = 1

        # Calculate total number of valid entries
        total_valid_states = len(valid_emotional_states)

        # Handle division by zero
        if total_valid_states == 0:
            log_metric_error("Emotional State Distribution", ValueError("No valid emotional states found"))
            return {}

        # Calculate proportions
        state_proportions = {state: count / total_valid_states for state, count in state_count.items()}

        return state_proportions

    except Exception as e:
        log_metric_error("Emotional State Distribution", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, safe_sum, log_metric_error

def Contact_Frequency_Analysis(data: Dict[str, Any]) -> Dict[str, int]:
    """
    Metric: Contact Frequency Analysis
    Description: Evaluates the frequency of interactions between agents to assess communication patterns.
    Visualization type: bar
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        Return a dictionary mapping categories to values
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Define bins for categorizing frequency of contact
        bins = {
            "low": (0, 5),
            "medium": (6, 15),
            "high": (16, float('inf'))
        }
        
        # Initialize results dictionary with bin categories
        result = {bin_name: 0 for bin_name in bins}

        # Access frequency_of_contact data from CommunicationAgent
        frequency_of_contact_list = safe_list(safe_get(data, 'frequency_of_contact', []))
        
        # Iterate over the list and categorize frequencies
        for frequency in frequency_of_contact_list:
            try:
                # Convert frequency to a number safely
                freq_value = safe_get({"value": frequency}, "value")
                if freq_value is None:
                    continue
                
                # Determine the appropriate bin for the frequency value
                for bin_name, (low, high) in bins.items():
                    if low <= freq_value <= high:
                        result[bin_name] += freq_value
                        break
            
            except Exception as inner_error:
                log_metric_error("Contact Frequency Analysis", inner_error, {"frequency": frequency})
                continue

        return result

    except Exception as e:
        log_metric_error("Contact Frequency Analysis", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {bin_name: 0 for bin_name in bins}

# Metric function registry
METRIC_FUNCTIONS = {
    'Average_Emotional_Intensity': Average_Emotional_Intensity,
    'Emotional_State_Distribution': Emotional_State_Distribution,
    'Contact_Frequency_Analysis': Contact_Frequency_Analysis,
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
