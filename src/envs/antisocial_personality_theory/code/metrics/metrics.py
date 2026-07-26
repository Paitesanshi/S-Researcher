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
from onesim.monitor.utils import safe_get, safe_list, log_metric_error

def Manipulation_Strategy_Distribution(data: Dict[str, Any]) -> Dict[str, int]:
    """
    Metric: Antisocial Behavior Frequency
    Description: Measures the frequency of antisocial behaviors exhibited by agents, based on their interaction status and manipulation strategy.
    Visualization type: bar
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Retrieve agent variables
        # interaction_status_list = safe_list(safe_get(data, 'interaction_status', []))
        manipulation_strategy_list = safe_list(safe_get(data, 'manipulation_strategy', []))


        # Initialize counts dictionary
        counts = {}


        # Process manipulation_strategy_list
        for strategy in manipulation_strategy_list:
            if strategy:  # Ensure strategy is not None or empty
                if strategy in counts:
                    counts[strategy] += 1
                else:
                    counts[strategy] = 1

        return counts

    except Exception as e:
        log_metric_error("Manipulation Strategy Distribution", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}


# Metric function registry
METRIC_FUNCTIONS = {
    'Manipulation_Strategy_Distribution': Manipulation_Strategy_Distribution,
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
