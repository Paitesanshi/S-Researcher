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

def average_dissonance_level(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: average_dissonance_level
    Description: Measures the average dissonance level experienced by Actor A across all scenarios.
    Visualization type: line
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        Return a dictionary mapping series names to values
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Access the dissonance_level values from Actor A
        dissonance_levels = safe_list(safe_get(data, 'dissonance_level', []))

        # Calculate the average dissonance level, ignoring None values
        average_dissonance = safe_avg(dissonance_levels, default=0)

        # Return the result in the format suitable for line visualization
        return {"average_dissonance_level": average_dissonance}
    except Exception as e:
        log_metric_error("average_dissonance_level", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {"average_dissonance_level": 0}

from typing import Dict, Any
from collections import Counter
from onesim.monitor.utils import safe_get, safe_list, log_metric_error

def feedback_quality_distribution(data: Dict[str, Any]) -> Dict[int, int]:
    """
    Metric: feedback_quality_distribution
    Description: Shows the distribution of feedback quality scores provided by Observer B.
    Visualization type: bar
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Access the feedback_quality data from ObserverB
        feedback_quality_list = safe_list(safe_get(data, 'feedback_quality', []))

        # Filter out None values and ensure all elements are integers
        valid_feedback_quality = [score for score in feedback_quality_list if isinstance(score, int)]

        # Count the occurrences of each feedback quality score
        distribution = Counter(valid_feedback_quality)

        return dict(distribution)
    
    except Exception as e:
        log_metric_error("feedback_quality_distribution", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, log_metric_error

def strategy_type_proportion(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: strategy_type_proportion
    Description: Represents the proportion of each strategy type chosen by Actor A to reduce dissonance.
    Visualization type: pie

    Args:
        data: Dictionary containing all variables; agent variables are lists

    Returns:

    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Access the strategy_type variable from ActorA
        strategy_types = safe_list(safe_get(data, 'strategy_type', []))

        # Filter out None values
        strategy_types = [s for s in strategy_types if s is not None]

        # Check if the list is empty after filtering
        if not strategy_types:
            return {}

        # Calculate the total number of strategies
        total_count = len(strategy_types)

        # Calculate the proportion of each unique strategy type
        strategy_count = {}
        for strategy in strategy_types:
            if strategy not in strategy_count:
                strategy_count[strategy] = 0
            strategy_count[strategy] += 1

        # Calculate proportions
        strategy_proportion = {strategy: count / total_count for strategy, count in strategy_count.items()}

        return strategy_proportion

    except Exception as e:
        log_metric_error("strategy_type_proportion", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

# Metric function registry
METRIC_FUNCTIONS = {
    'average_dissonance_level': average_dissonance_level,
    'feedback_quality_distribution': feedback_quality_distribution,
    'strategy_type_proportion': strategy_type_proportion,
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
