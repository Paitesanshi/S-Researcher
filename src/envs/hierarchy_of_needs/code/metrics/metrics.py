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

def Physiological_Needs_Fulfillment_Rate(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Physiological Needs Fulfillment Rate
    Description: Measures the proportion of PhysiologicalAgents whose physiological needs are marked as 'fulfilled'.
    Visualization type: pie
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Access physiological_needs_status list from the data
        physiological_needs_status_list = safe_list(safe_get(data, 'physiological_needs_status', []))

        # Count fulfilled and unfulfilled statuses
        fulfilled_count = safe_count(physiological_needs_status_list, lambda status: status != 'awaiting_input')
        unfulfilled_count = safe_count(physiological_needs_status_list, lambda status: status == 'awaiting_input')

        # Total count of agents
        total_agents = fulfilled_count + unfulfilled_count

        if total_agents == 0:
            # Handle division by zero scenario
            log_metric_error("Physiological Needs Fulfillment Rate", ZeroDivisionError("No agents to calculate fulfillment rate"), {"data_keys": list(data.keys())})
            return {'Fulfilled': 0, 'Unfulfilled': 0}

        # Calculate proportions
        fulfilled_rate = fulfilled_count / total_agents
        unfulfilled_rate = unfulfilled_count / total_agents

        # Return result for pie chart visualization
        return {'Fulfilled': fulfilled_rate, 'Unfulfilled': unfulfilled_rate}

    except Exception as e:
        log_metric_error("Physiological Needs Fulfillment Rate", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {'Fulfilled': 0, 'Unfulfilled': 0}

from typing import Dict, Any
from onesim.monitor.utils import (
    safe_get, safe_list, safe_avg, log_metric_error
)

def Average_Social_Interactions_Needed(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Average Social Interactions Needed
    Description: Calculates the average number of social interactions needed by SocialAgents to satisfy their social needs.
    Visualization type: bar
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Access the 'social_interactions_needed' variable from the data
        social_interactions_needed_list = safe_list(safe_get(data, 'social_interactions_needed', []))

        # Calculate the average number of interactions needed
        # Treat None or empty lists as zero
        average_interactions = safe_avg(social_interactions_needed_list)

        # Return the result in the format for a bar chart
        return {"Average Social Interactions Needed": average_interactions}

    except Exception as e:
        log_metric_error("Average Social Interactions Needed", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {"Average Social Interactions Needed": 0.0}

from typing import Dict, Any, List
from onesim.monitor.utils import safe_get, safe_list, safe_count, log_metric_error

def Self_Actualization_Goals_Progress(data: Dict[str, Any]) -> Dict[str, List[float]]:
    """
    Metric: Self_Actualization Goals Progress
    Description: Tracks the progress of SelfActualizationAgents towards their self-actualization goals.
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
        # Access agent variables
        goals_list = safe_list(safe_get(data, 'self_actualization_goals', []))
        status_list = safe_list(safe_get(data, 'self_actualization_status', []))

        # Validate that both lists are of the same length
        if len(goals_list) != len(status_list):
            log_metric_error("Self-Actualization Goals Progress", ValueError("Mismatched list lengths"), {"goals_list": len(goals_list), "status_list": len(status_list)})
            return {}

        # Initialize the result dictionary
        progress_dict = {}

        # Calculate progress for each agent
        for i, (goals, status) in enumerate(zip(goals_list, status_list)):
            try:
                # Ensure goals is a list and status is a valid number of completed goals
                goals = safe_list(goals)
                total_goals = len(goals)
                completed_goals = safe_count(goals, lambda x: x == status)

                # Skip if total_goals is zero to avoid division by zero
                if total_goals > 0:
                    progress_ratio = completed_goals / total_goals
                else:
                    progress_ratio = 0.0

                # Add progress to the dictionary
                progress_dict[f'agent_{i+1}'] = [progress_ratio]

            except Exception as agent_error:
                log_metric_error("Self-Actualization Goals Progress", agent_error, {"agent_index": i})

        return progress_dict

    except Exception as e:
        log_metric_error("Self-Actualization Goals Progress", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

# Metric function registry
METRIC_FUNCTIONS = {
    'Physiological_Needs_Fulfillment_Rate': Physiological_Needs_Fulfillment_Rate,
    'Average_Social_Interactions_Needed': Average_Social_Interactions_Needed,
    'Self_Actualization_Goals_Progress': Self_Actualization_Goals_Progress,
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
