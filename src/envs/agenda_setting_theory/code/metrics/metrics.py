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
from onesim.monitor.utils import safe_get, safe_list, safe_sum, log_metric_error

def Public_Focus_Distribution(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Public Focus Distribution
    Description: Measures the distribution of focus values across all Public Agents to understand how media reporting affects public attention.
    Visualization type: pie
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Access the list of focus values from PublicAgent
        focus_values = safe_list(safe_get(data, 'focus_value', []))
        
        # Handle None values by treating them as zero focus
        valid_focus_values = [safe_sum([value], default=0) for value in focus_values if value is not None]

        # If the list is empty, return an empty dictionary
        if not valid_focus_values:
            return {}

        # Calculate the total focus to determine proportions
        total_focus = safe_sum(valid_focus_values, default=0)
        if total_focus == 0:
            return {}

        # Calculate the proportion of focus for each unique focus value
        focus_distribution = {}
        for value in valid_focus_values:
            if value not in focus_distribution:
                focus_distribution[value] = 0
            focus_distribution[value] += value

        # Convert counts to proportions
        for key in focus_distribution:
            focus_distribution[key] /= total_focus

        return focus_distribution

    except Exception as e:
        log_metric_error("Public Focus Distribution", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

from typing import Dict, Any, List
from onesim.monitor.utils import safe_get, safe_list, safe_avg, log_metric_error

def Media_Reporting_Frequency_Analysis(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Media Reporting Frequency Analysis
    Description: Analyzes the average reporting frequency of topics by Media Agents to assess media emphasis.
    Visualization type: bar
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Access and validate the required variables
        reporting_frequencies = safe_list(safe_get(data, 'reporting_frequency', []))
        selected_topics = safe_list(safe_get(data, 'selected_topic', []))

        if not reporting_frequencies or not selected_topics:
            return {}

        # Pair the reporting frequencies with their respective selected topics
        topic_frequency_map = {}
        for frequency, topic in zip(reporting_frequencies, selected_topics):
            if frequency is None or topic is None:
                continue

            try:
                frequency = int(frequency)
            except (ValueError, TypeError):
                log_metric_error("Media Reporting Frequency Analysis", ValueError("Invalid frequency value"), {"frequency": frequency})
                continue

            if topic not in topic_frequency_map:
                topic_frequency_map[topic] = []

            topic_frequency_map[topic].append(frequency)

        # Calculate the average reporting frequency for each topic
        avg_frequency_per_topic = {}
        for topic, frequencies in topic_frequency_map.items():
            if frequencies:
                avg_frequency_per_topic[topic] = safe_avg(frequencies)

        return avg_frequency_per_topic

    except Exception as e:
        log_metric_error("Media Reporting Frequency Analysis", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

from typing import Dict, Any
from onesim.monitor.utils import safe_get, safe_number, safe_list, safe_avg, log_metric_error

def Emotional_Tone_Impact(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Metric: Emotional Tone Impact
    Description: Evaluates the impact of emotional tone used by Media Agents on public focus values.
    Visualization Type: line

    Args:
        data: Dictionary containing all variables collected by the monitor. Note that agent variables are lists.

    Returns:
        A dictionary where keys are emotional tones and values are average focus values.

    Note:
        This function handles various edge cases including None values, empty lists, and type errors.
    """
    try:
        # Initialize result dictionary
        result = {}

        # Retrieve emotional tones and focus values from data
        emotional_tones = safe_list(safe_get(data, 'emotional_tone', []))
        focus_values = safe_list(safe_get(data, 'focus_value', []))

        # Check if lists are empty
        if not emotional_tones or not focus_values:
            return result

        # Dictionary to hold sum and count for each emotional tone
        tone_impact = {}

        # Iterate over emotional tones and corresponding focus values
        for tone, focus in zip(emotional_tones, focus_values):
            # Ensure tone is a valid string and focus is a valid number
            if tone is None or not isinstance(tone, str):
                continue
            focus_value = safe_number(focus, default=0)

            if tone not in tone_impact:
                tone_impact[tone] = {'sum': 0, 'count': 0}

            tone_impact[tone]['sum'] += focus_value
            tone_impact[tone]['count'] += 1

        # Calculate average focus values for each emotional tone
        for tone, data in tone_impact.items():
            if data['count'] > 0:
                result[tone] = data['sum'] / data['count']
            else:
                result[tone] = 0

        return result

    except Exception as e:
        log_metric_error("Emotional Tone Impact", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

# Metric function registry
METRIC_FUNCTIONS = {
    'Public_Focus_Distribution': Public_Focus_Distribution,
    'Media_Reporting_Frequency_Analysis': Media_Reporting_Frequency_Analysis,
    'Emotional_Tone_Impact': Emotional_Tone_Impact,
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
