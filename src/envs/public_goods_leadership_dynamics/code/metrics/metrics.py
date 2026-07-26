# -*- coding: utf-8 -*-
"""
Public Goods Leadership Dynamics - Metrics Module
Analyzes leader contributions, follower responses, and decision mechanism effects
"""

from typing import Dict, Any, List, Optional, Callable
import statistics
from loguru import logger
from onesim.monitor.utils import (
    safe_get, safe_number, safe_list, safe_sum, 
    safe_avg, safe_max, safe_min, safe_count, log_metric_error
)


def Average_Follower_Contribution(data: Dict[str, Any]) -> Any:
    """
    Calculate average follower contribution level
    
    This metric measures follower cooperation levels in response to leader behavior.
    
    Visualization: line chart
    Returns: {"Average Follower Contribution": <value>}
    """
    try:
        if not data or not isinstance(data, dict):
            log_metric_error("Average_Follower_Contribution", ValueError("Invalid data"), {"data": data})
            return {"Average Follower Contribution": 0}

        # Get follower contributions
        follower_contributions = safe_list(safe_get(data, 'follower_contributions', []))
        
        if not follower_contributions:
            return {"Average Follower Contribution": 0}

        # Filter valid numbers
        valid_contributions = [safe_number(c) for c in follower_contributions if c is not None]
        
        if not valid_contributions:
            return {"Average Follower Contribution": 0}

        avg_contribution = safe_avg(valid_contributions)
        
        return {"Average Follower Contribution": round(avg_contribution, 2)}
    
    except Exception as e:
        log_metric_error("Average_Follower_Contribution", e, {"data_keys": list(data.keys())})
        return {"Average Follower Contribution": 0}



def Follower_Contribution_by_Trait(data: Dict[str, Any]) -> Any:
    """
    Calculate average follower contributions grouped by trait (Prosocial vs Proself)
    
    This metric tests whether follower personality traits affect cooperation levels.
    
    Visualization: bar chart
    Returns: {"Prosocial": <avg>, "Proself": <avg>}
    """
    try:
        if not data or not isinstance(data, dict):
            log_metric_error("Follower_Contribution_by_Trait", ValueError("Invalid data"), {"data": data})
            return {"Prosocial": 0, "Proself": 0}

        # Get follower contributions and traits
        follower_contributions = safe_list(safe_get(data, 'follower_contributions', []))
        follower_traits = safe_list(safe_get(data, 'follower_traits', []))
        
        if not follower_contributions or not follower_traits:
            return {"Prosocial": 0, "Proself": 0}

        # Group contributions by trait
        trait_groups = {"Prosocial": [], "Proself": []}
        
        for i, trait in enumerate(follower_traits):
            if i < len(follower_contributions) and trait is not None:
                contrib = safe_number(follower_contributions[i])
                trait_str = str(trait)
                
                if trait_str in trait_groups:
                    trait_groups[trait_str].append(contrib)
        
        # Calculate averages for each trait
        result = {}
        for trait, contributions in trait_groups.items():
            if contributions:
                result[trait] = round(safe_avg(contributions), 2)
            else:
                result[trait] = 0
        
        return result
    
    except Exception as e:
        log_metric_error("Follower_Contribution_by_Trait", e, {"data_keys": list(data.keys())})
        return {"Prosocial": 0, "Proself": 0}




def Leader_Follower_Comparison(data: Dict[str, Any]) -> Any:
    """
    Compare leader vs follower average contributions
    
    This metric shows whether followers match, exceed, or fall below leader contributions.
    
    Visualization: bar chart
    Returns: {"Leader": <avg>, "Followers": <avg>}
    """
    try:
        if not data or not isinstance(data, dict):
            log_metric_error("Leader_Follower_Comparison", ValueError("Invalid data"), {"data": data})
            return {"Leader": 0, "Followers": 0}

        # Get contributions
        leader_contributions = safe_list(safe_get(data, 'leader_contributions', []))
        follower_contributions = safe_list(safe_get(data, 'follower_contributions', []))
        
        # Calculate averages
        leader_avg = 0
        if leader_contributions:
            valid_leader = [safe_number(c) for c in leader_contributions if c is not None]
            if valid_leader:
                leader_avg = safe_avg(valid_leader)
        
        follower_avg = 0
        if follower_contributions:
            valid_follower = [safe_number(c) for c in follower_contributions if c is not None]
            if valid_follower:
                follower_avg = safe_avg(valid_follower)
        
        return {
            "Leader": round(leader_avg, 2),
            "Followers": round(follower_avg, 2)
        }
    
    except Exception as e:
        log_metric_error("Leader_Follower_Comparison", e, {"data_keys": list(data.keys())})
        return {"Leader": 0, "Followers": 0}


def Follower_Contribution_Distribution(data: Dict[str, Any]) -> Any:
    """
    Show distribution of follower contributions across different levels
    
    This metric categorizes follower contributions into groups to visualize
    the spread of cooperation levels: Free-riders (0), Low (1-3), Medium (4-7), High (8-10).
    
    Visualization: pie chart
    Returns: {"Free-riders (0)": <count>, "Low (1-3)": <count>, "Medium (4-7)": <count>, "High (8-10)": <count>}
    """
    try:
        if not data or not isinstance(data, dict):
            log_metric_error("Follower_Contribution_Distribution", ValueError("Invalid data"), {"data": data})
            return {}

        # Get follower contributions
        follower_contributions = safe_list(safe_get(data, 'follower_contributions', []))
        
        if not follower_contributions:
            return {}

        # Initialize distribution categories
        distribution = {}
        
        # Categorize each contribution
        for contribution in follower_contributions:
            if contribution is None:
                continue
            
            contrib_value = safe_number(contribution)
            
            if contrib_value not in distribution:
                distribution[contrib_value] = 0
            distribution[contrib_value] += 1

        return {str(k): v for k, v in distribution.items()}
    
    except Exception as e:
        log_metric_error("Follower_Contribution_Distribution", e, {"data_keys": list(data.keys())})
        return {}


# Metric function registry
METRIC_FUNCTIONS = {
    'Average_Follower_Contribution': Average_Follower_Contribution,
    'Follower_Contribution_by_Trait': Follower_Contribution_by_Trait,
    'Leader_Follower_Comparison': Leader_Follower_Comparison,
    'Follower_Contribution_Distribution': Follower_Contribution_Distribution,
}


def get_metric_function(function_name: str) -> Optional[Callable]:
    """
    Get metric calculation function by name
    
    Args:
        function_name: Name of the metric function
        
    Returns:
        Metric calculation function or None
    """
    return METRIC_FUNCTIONS.get(function_name)
