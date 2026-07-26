# -*- coding: utf-8 -*-
"""
"""

from typing import Dict, Any, List, Optional, Union, Callable
import math
from collections import Counter, defaultdict
from loguru import logger
from onesim.monitor.utils import (
    safe_get, safe_number, safe_list, safe_sum, 
    safe_avg, safe_max, safe_min, safe_count, log_metric_error
)


def calculate_cultural_distribution(data: Dict[str, Any]) -> Any:
    """
    Metric: cultural_distribution
    Visualization type: line
    
    """
    try:
        if not data or not isinstance(data, dict):
            log_metric_error("cultural_distribution", ValueError("Invalid data input"), {"data": data})
            return {}

        dimensions = [
            "music_preference",
            "culinary_preference", 
            "fashion_style", 
            "political_orientation", 
            "leisure_activity"
        ]
        
        results = {}
        
        for dimension in dimensions:
            dimension_values = safe_list(safe_get(data, dimension, []))
            
            valid_values = [value for value in dimension_values if value]
            
            if not valid_values:
                continue
            
            value_counts = Counter(valid_values)
            
            results[dimension] = dict(value_counts)
        
        return results
    
    except Exception as e:
        log_metric_error("cultural_distribution", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}


def calculate_cultural_homogeneity(data: Dict[str, Any]) -> Any:
    """
    Metric: cultural_homogeneity
    Visualization type: line
    
    """
    try:
        if not data or not isinstance(data, dict):
            log_metric_error("cultural_homogeneity", ValueError("Invalid data input"), {"data": data})
            return 0
        
        dimensions = [
            "music_preference",
            "culinary_preference", 
            "fashion_style", 
            "political_orientation", 
            "leisure_activity"
        ]
        
        homogeneity_indices = []
        
        for dimension in dimensions:
            dimension_values = safe_list(safe_get(data, dimension, []))
            
            valid_values = [value for value in dimension_values if value]
            
            if not valid_values:
                continue
            
            value_counts = Counter(valid_values)
            
            total_agents = len(valid_values)
            most_common_value, most_common_count = value_counts.most_common(1)[0]
            dimension_homogeneity = most_common_count / total_agents
            
            homogeneity_indices.append(dimension_homogeneity)
        
        if not homogeneity_indices:
            return 0
        
        return sum(homogeneity_indices) / len(homogeneity_indices)
    
    except Exception as e:
        log_metric_error("cultural_homogeneity", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return 0


def calculate_adoption_rate(data: Dict[str, Any]) -> Any:
    """
    Metric: adoption_rate
    Visualization type: line
    
    """
    try:
        if not data or not isinstance(data, dict):
            log_metric_error("adoption_rate", ValueError("Invalid data input"), {"data": data})
            return 0
        
        current_round = safe_number(safe_get(data, "round_number", 0))
        
        adoption_histories = safe_list(safe_get(data, "adoption_history", []))
        
        if not adoption_histories:
            return 0
        
        total_recommendations = 0
        successful_adoptions = 0
        
        for agent_history in adoption_histories:
            if not isinstance(agent_history, list):
                continue
                
            for entry in agent_history:
                if not isinstance(entry, dict):
                    continue
                    
                entry_round = safe_number(entry.get("round", -1))
                
                if entry_round == current_round:
                    total_recommendations += 1
                    if entry.get("adopted", False):
                        successful_adoptions += 1
        
        if total_recommendations == 0:
            return 0
            
        adoption_rate = successful_adoptions / total_recommendations
        return adoption_rate
    
    except Exception as e:
        log_metric_error("adoption_rate", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return 0


def calculate_cultural_regions(data: Dict[str, Any]) -> Any:
    """
    Metric: cultural_regions
    Visualization type: line
    
    """
    try:
        if not data or not isinstance(data, dict):
            log_metric_error("cultural_regions", ValueError("Invalid data input"), {"data": data})
            return {}
        
        dimensions = [
            "music_preference",
            "culinary_preference", 
            "fashion_style", 
            "political_orientation", 
            "leisure_activity"
        ]
        
        relationships = safe_list(safe_get(data, "agent_relationships", []))
        
        adjacency = defaultdict(list)
        for rel in relationships:
            if not isinstance(rel, dict):
                continue
                
            source = rel.get("source_id")
            target = rel.get("target_id")
            
            if source and target:
                adjacency[source].append(target)
                adjacency[target].append(source)  # Relationships are assumed to be bidirectional
        
        results = {}
        
        for dimension in dimensions:
            agent_values = {}
            dimension_values = safe_get(data, dimension, {})
            
            if not isinstance(dimension_values, dict):
                continue
            
            for agent_id, value in dimension_values.items():
                if value:  # Consider valid values only
                    agent_values[agent_id] = value
            
            visited = set()
            region_count = 0
            
            for agent_id in agent_values:
                if agent_id in visited:
                    continue
                    
                value = agent_values[agent_id]
                region_count += 1
                
                queue = [agent_id]
                visited.add(agent_id)
                
                while queue:
                    current = queue.pop(0)
                    
                    for neighbor in adjacency[current]:
                        if neighbor not in visited and agent_values.get(neighbor) == value:
                            visited.add(neighbor)
                            queue.append(neighbor)
            
            results[dimension] = region_count
        
        if results:
            results["average"] = sum(results.values()) / len(results)
        
        return results
    
    except Exception as e:
        log_metric_error("cultural_regions", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}


def calculate_influence_distribution(data: Dict[str, Any]) -> Any:
    """
    Metric: influence_distribution
    Visualization type: bar
    
    """
    try:
        if not data or not isinstance(data, dict):
            log_metric_error("influence_distribution", ValueError("Invalid data input"), {"data": data})
            return {}
        
        adoption_histories = safe_list(safe_get(data, "adoption_history", []))
        
        influence_counts = Counter()
        
        for agent_history in adoption_histories:
            if not isinstance(agent_history, list):
                continue
                
            for entry in agent_history:
                if not isinstance(entry, dict):
                    continue
                    
                if entry.get("adopted", False):
                    recommender = entry.get("recommender")
                    if recommender:
                        influence_counts[recommender] += 1
        
        return dict(influence_counts)
    
    except Exception as e:
        log_metric_error("influence_distribution", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}


def calculate_dimension_influence(data: Dict[str, Any]) -> Any:
    """
    Metric: dimension_influence
    Visualization type: bar
    
    """
    try:
        if not data or not isinstance(data, dict):
            log_metric_error("dimension_influence", ValueError("Invalid data input"), {"data": data})
            return {}
        
        dimensions = [
            "music_preference",
            "culinary_preference", 
            "fashion_style", 
            "political_orientation", 
            "leisure_activity"
        ]
        
        adoption_histories = safe_list(safe_get(data, "adoption_history", []))
        
        dimension_counts = Counter()
        
        for agent_history in adoption_histories:
            if not isinstance(agent_history, list):
                continue
                
            for entry in agent_history:
                if not isinstance(entry, dict):
                    continue
                    
                if entry.get("adopted", False):
                    dimension = entry.get("dimension")
                    if dimension in dimensions:
                        dimension_counts[dimension] += 1
        
        return dict(dimension_counts)
    
    except Exception as e:
        log_metric_error("dimension_influence", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}


# Metric function registry
METRIC_FUNCTIONS = {
    'calculate_cultural_distribution': calculate_cultural_distribution,
    'calculate_cultural_homogeneity': calculate_cultural_homogeneity,
    'calculate_adoption_rate': calculate_adoption_rate,
    'calculate_cultural_regions': calculate_cultural_regions,
    'calculate_influence_distribution': calculate_influence_distribution,
    'calculate_dimension_influence': calculate_dimension_influence,
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


def test_metric_function(function_name: str, test_data: Dict[str, Any]) -> Any:
    """
    Test the metric calculation function
    
    Args:
        function_name: Function name
        test_data: test data
        
    Returns:
    """
    func = get_metric_function(function_name)
    if func is None:
        raise ValueError(f"Metric function not found: {function_name}")
    
    try:
        result = func(test_data)
        print(f"Metric {function_name} result: {result}")
        return result
    except Exception as e:
        log_metric_error(function_name, e, {"test_data": test_data})
        raise


def generate_test_data() -> Dict[str, Any]:
    """
    
    Returns:
    """
    return {
        "round_number": 5,
        
        "music_preference": {
            "agent1": "Classical",
            "agent2": "Rock",
            "agent3": "Classical",
            "agent4": "Pop",
            "agent5": "Electronic",
            "agent6": "Folk/Traditional",
            "agent7": "Classical",
            "agent8": "Rock",
            "agent9": "Pop",
            "agent10": "Classical"
        },
        "culinary_preference": {
            "agent1": "Traditional Local",
            "agent2": "International",
            "agent3": "Traditional Local",
            "agent4": "Fast Food",
            "agent5": "Vegetarian/Organic",
            "agent6": "Gourmet/Experimental",
            "agent7": "Traditional Local",
            "agent8": "International",
            "agent9": "Fast Food",
            "agent10": "Traditional Local"
        },
        "fashion_style": {
            "agent1": "Formal/Professional",
            "agent2": "Casual/Relaxed",
            "agent3": "Formal/Professional",
            "agent4": "Athletic/Sporty",
            "agent5": "Artistic/Alternative",
            "agent6": "Luxury/High-fashion",
            "agent7": "Formal/Professional",
            "agent8": "Casual/Relaxed",
            "agent9": "Athletic/Sporty",
            "agent10": "Formal/Professional"
        },
        "political_orientation": {
            "agent1": "Conservative",
            "agent2": "Progressive",
            "agent3": "Conservative",
            "agent4": "Centrist/Moderate",
            "agent5": "Libertarian",
            "agent6": "Green/Environmental",
            "agent7": "Conservative",
            "agent8": "Progressive",
            "agent9": "Centrist/Moderate",
            "agent10": "Conservative"
        },
        "leisure_activity": {
            "agent1": "Sports/Fitness",
            "agent2": "Arts/Creative Pursuits",
            "agent3": "Sports/Fitness",
            "agent4": "Social Gatherings",
            "agent5": "Media/Entertainment",
            "agent6": "Nature/Outdoors",
            "agent7": "Sports/Fitness",
            "agent8": "Arts/Creative Pursuits",
            "agent9": "Social Gatherings",
            "agent10": "Sports/Fitness"
        },
        
        "adoption_history": [
            [
                {"round": 5, "adopted": True, "recommender": "agent1", "dimension": "music_preference"},
                {"round": 3, "adopted": False, "recommender": "agent2", "dimension": "fashion_style"}
            ],
            [
                {"round": 5, "adopted": False, "recommender": "agent3", "dimension": "culinary_preference"}
            ],
            [
                {"round": 4, "adopted": True, "recommender": "agent1", "dimension": "political_orientation"},
                {"round": 5, "adopted": True, "recommender": "agent7", "dimension": "leisure_activity"}
            ]
        ],
        
        "agent_relationships": [
            {"source_id": "agent1", "target_id": "agent2"},
            {"source_id": "agent1", "target_id": "agent3"},
            {"source_id": "agent2", "target_id": "agent4"},
            {"source_id": "agent3", "target_id": "agent5"},
            {"source_id": "agent4", "target_id": "agent6"},
            {"source_id": "agent5", "target_id": "agent7"},
            {"source_id": "agent6", "target_id": "agent8"},
            {"source_id": "agent7", "target_id": "agent9"},
            {"source_id": "agent8", "target_id": "agent10"},
            {"source_id": "agent9", "target_id": "agent1"}
        ]
    }


def test_all_metrics(test_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Test all metric functions
    
    Args:
        
    Returns:
    """
    if test_data is None:
        test_data = generate_test_data()
        
    results = {}
    for func_name, func in METRIC_FUNCTIONS.items():
        try:
            result = func(test_data)
            results[func_name] = result
        except Exception as e:
            results[func_name] = f"ERROR: {str(e)}"
            log_metric_error(func_name, e, {"test_data": test_data})
    
    return results


# Run metric tests when this module is executed directly
if __name__ == "__main__":
    
    print("Generating test data...")
    test_data = generate_test_data()
    
    print("Test all metric functions...")
    results = test_all_metrics(test_data)
    
    print("\nTest results:")
    for func_name, result in results.items():
        print(f"{func_name}: {result}")