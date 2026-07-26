# -*- coding: utf-8 -*-
"""
Auto-generated monitoring metric calculation module
"""

from typing import Dict, Any, List, Optional, Union, Callable
import math
from loguru import logger
from typing import Dict, Any
from onesim.monitor.utils import (
    safe_get, safe_number, safe_list, safe_sum, 
    safe_avg, safe_max, safe_min, safe_count, log_metric_error
)
from onesim.monitor.utils import safe_get, safe_list, safe_sum, safe_count, safe_number, log_metric_error

def Candidate_Selection_Distribution(data: Dict[str, Any]) -> Dict[str, int]:
    """
    Metric: Candidate Selection Distribution
    Description: Examines the distribution of selected candidates among the voters.
    Visualization type: bar
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Access the list of selected candidate IDs from VoterAgent
        selected_candidate_ids = safe_list(safe_get(data, 'selected_candidate_id', []))

        # Initialize a dictionary to store the count of votes for each candidate
        candidate_vote_count = {}

        # Iterate over the list of selected candidate IDs
        for candidate_id in selected_candidate_ids:
            # Skip None values
            if candidate_id is None:
                continue
            
            # Count occurrences of each candidate ID
            if candidate_id in candidate_vote_count:
                candidate_vote_count[candidate_id] += 1
            else:
                candidate_vote_count[candidate_id] = 1

        # Return the result in the format suitable for a bar chart
        return candidate_vote_count

    except Exception as e:
        log_metric_error("Candidate Selection Distribution", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

# Metric function registry
METRIC_FUNCTIONS = {
    'Candidate_Selection_Distribution': Candidate_Selection_Distribution,
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
