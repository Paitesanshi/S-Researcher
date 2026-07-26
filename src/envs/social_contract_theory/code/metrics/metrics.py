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

def Agent_Negotiation_Success_Rate(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Agent Negotiation Success Rate
    Description: Measures the proportion of successful negotiations by Individual Agents.
    Visualization type: pie
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        Return a dictionary mapping categories to values
    """
    try:
        # Access negotiation_status list for IndividualAgent
        negotiation_status_list = safe_list(safe_get(data, 'negotiation_status', []))

        if not negotiation_status_list:
            # If the list is empty, log an error and return default values
            log_metric_error("Agent Negotiation Success Rate", ValueError("Empty negotiation_status list"), {"data": data})
            return {"successful": 0.0, "unsuccessful": 1.0}

        # Count successful negotiations
        successful_count = safe_count(negotiation_status_list, lambda status: status == 'successful')

        # Count unsuccessful negotiations (including None or invalid types treated as unsuccessful)
        unsuccessful_count = len(negotiation_status_list) - successful_count

        # Handle division by zero scenario
        total_count = len(negotiation_status_list)
        if total_count == 0:
            log_metric_error("Agent Negotiation Success Rate", ZeroDivisionError("Total negotiation count is zero"), {"data": data})
            return {"successful": 0.0, "unsuccessful": 1.0}

        # Calculate proportions
        successful_rate = successful_count / total_count
        unsuccessful_rate = unsuccessful_count / total_count

        # Return result as a pie chart data structure
        result = {"successful": successful_rate, "unsuccessful": unsuccessful_rate}
        return result

    except Exception as e:
        log_metric_error("Agent Negotiation Success Rate", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {"successful": 0.0, "unsuccessful": 1.0}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, safe_count, log_metric_error

def Government_Enforcement_Rate(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Metric: Government Enforcement Rate
    Description: Tracks the enforcement status of laws by Government Agents over time.
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
        # Access the enforcement_status list for GovernmentAgent
        enforcement_status_list = safe_list(safe_get(data, 'enforcement_status', []))
        logger.info(f"enforcement_status_list: {enforcement_status_list}")
        
        # Count the number of 'enforced' statuses
        enforced_count = safe_count(enforcement_status_list, lambda x: x == 'enforced')
        
        # Prepare the result for line visualization
        result = {'Government Enforcement Rate': enforced_count}
        
        return result
    except Exception as e:
        log_metric_error("Government Enforcement Rate", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {'Government Enforcement Rate': 0}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_list, safe_sum, log_metric_error

def Public_Policy_Impact_Analysis(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Public Policy Impact Analysis
    Description: Evaluates the results of impact analyses conducted by Public Policy Agents.
    Visualization type: bar
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        Return a dictionary mapping categories to values
    """
    try:
        # Initialize result dictionary
        result = {}

        # Access 'impact_analysis_results' from PublicPolicyAgent
        impact_analysis_results_list = safe_list(safe_get(data, 'impact_analysis_results', []))

        # Iterate through each agent's impact analysis results
        for index, impact_analysis_results in enumerate(impact_analysis_results_list):
            # Validate the impact_analysis_results as a dictionary
            if not isinstance(impact_analysis_results, dict):
                log_metric_error("Public Policy Impact Analysis", TypeError("Impact analysis results must be a dictionary"), {"agent_index": index})
                continue

            # Sum up the values in the impact_analysis_results dictionary, skipping None values
            for key, value in impact_analysis_results.items():
                if value is None:
                    continue
                try:
                    numeric_value = safe_sum([value])
                except Exception as e:
                    log_metric_error("Public Policy Impact Analysis", e, {"agent_index": index, "key": key})
                    continue

                # Accumulate the sums for each metric key
                if key not in result:
                    result[key] = numeric_value
                else:
                    result[key] += numeric_value

        return result

    except Exception as e:
        log_metric_error("Public Policy Impact Analysis", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

# Metric function registry
METRIC_FUNCTIONS = {
    'Agent_Negotiation_Success_Rate': Agent_Negotiation_Success_Rate,
    'Government_Enforcement_Rate': Government_Enforcement_Rate,
    'Public_Policy_Impact_Analysis': Public_Policy_Impact_Analysis,
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
