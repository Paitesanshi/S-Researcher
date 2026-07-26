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


def average_job_seeker_experience(data: Dict[str, Any]) -> Any:
    """
    Metric: average_job_seeker_experience
    Description: Measures the average years of experience among job seekers, providing insights into the overall experience level of the job-seeking population.
    Visualization type: bar
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        - line: Return a scalar value
        - bar/pie: Return a dictionary mapping categories to values
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    from onesim.monitor.utils import (
        safe_get, safe_list, safe_sum, safe_count, log_metric_error
    )
    
    try:
        # Validate the input data structure
        if not data or not isinstance(data, dict):
            log_metric_error("average_job_seeker_experience", ValueError("Invalid data input"), {"data": data})
            return {}

        # Extract the experience data from JobSeeker agents
        experience_list = safe_list(safe_get(data, "experience", []))
        # job_seekers = safe_get(data, "JobSeeker", [])
        # experience_list = []
        
        # for job_seeker in safe_list(job_seekers):
        #     experience = safe_get(job_seeker, "experience", None)
        #     if isinstance(experience, int):
        #         experience_list.append(experience)
        
        # Calculate the average experience
        total_experience = safe_sum(experience_list)
        count_experience = safe_count(experience_list)
        
        # Handle division by zero
        average_experience = total_experience / count_experience if count_experience > 0 else 0
        
        # Return result as a dictionary for bar visualization
        return {"Average Experience": average_experience}
    
    except Exception as e:
        log_metric_error("average_job_seeker_experience", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

from typing import Dict, Any
from onesim.monitor.utils import (
    safe_get,
    safe_list,
    safe_count,
    log_metric_error
)

def job_application_success_rate(data: Dict[str, Any]) -> Any:
    """
    Metric: job_application_success_rate
    Description: Measures the proportion of job applications that result in successful negotiations, indicating the efficiency of job matching and negotiation processes.
    Visualization type: pie
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        - line: Return a scalar value
        - bar/pie: Return a dictionary mapping categories to values
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    try:
        # Check if required variables exist and validate input data
        if not data or not isinstance(data, dict):
            log_metric_error("job_application_success_rate", ValueError("Invalid data input"), {"data": data})
            return {}

        # logger.info(f"data: {data}")
        # Retrieve and validate the applications_submitted and negotiation_outcomes
        applications_submitted = safe_list(safe_get(data, "applications_submitted", []))
        negotiation_outcomes = safe_list(safe_get(data, "negotiation_outcomes", []))

        # Check if the lists are valid
        if not applications_submitted or not negotiation_outcomes:
            log_metric_error("job_application_success_rate", ValueError("Missing or invalid input lists"), {
                "applications_submitted": applications_submitted,
                "negotiation_outcomes": negotiation_outcomes
            })
            return {"Success": 0.0, "Failure": 1.0}

        # Count the total number of applications submitted
        total_applications = safe_count(applications_submitted)

        # Count the number of successful negotiation outcomes
        successful_negotiations = safe_count(negotiation_outcomes, lambda outcome: outcome is not None and outcome)

        # Calculate success rate
        if total_applications == 0:
            success_rate = 0.0
        else:
            success_rate = successful_negotiations / total_applications

        # Return the result in a format suitable for a pie chart
        return {"Success": success_rate, "Failure": 1.0 - success_rate}

    except Exception as e:
        log_metric_error("job_application_success_rate", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {"Success": 0.0, "Failure": 1.0}

def employer_screening_efficiency(data: Dict[str, Any]) -> Any:
    """
    Metric: employer_screening_efficiency
    Description: Evaluates the efficiency of employers in screening candidates by comparing the number of screened candidates to the number of posted jobs.
    Visualization type: bar
    
    Args:
        data: Dictionary containing all variables; agent variables are lists
        
    Returns:
        - line: Return a scalar value
        - bar/pie: Return a dictionary mapping categories to values
        
    Notes:
        This function handles None values, empty lists, and type errors
    """
    from onesim.monitor.utils import (
        safe_get, safe_list, safe_sum, log_metric_error
    )
    
    try:
        logger.info(f"Screendata: {data}")
        # Validate input data
        if not data or not isinstance(data, dict):
            log_metric_error("employer_screening_efficiency", ValueError("Invalid data input"), {"data": data})
            return {}

        # Retrieve and validate screened_candidates and posted_jobs
        screened_candidates_list = safe_list(safe_get(data, "screened_candidates"))
        posted_jobs_list = safe_list(safe_get(data, "posted_jobs"))

        # Calculate total number of screened candidates
        total_screened_candidates = len([item for sublist in screened_candidates_list for item in sublist])

        # Calculate total number of posted jobs
        total_posted_jobs = len([item for sublist in posted_jobs_list for item in sublist])

        # Handle division by zero scenario
        if total_posted_jobs == 0:
            log_metric_error("employer_screening_efficiency", ZeroDivisionError("Total posted jobs is zero"), {
                "total_screened_candidates": total_screened_candidates,
                "total_posted_jobs": total_posted_jobs
            })
            efficiency = 0.0
        else:
            efficiency = total_screened_candidates / total_posted_jobs

        # Return result in appropriate format for bar visualization
        return {"employer_screening_efficiency": efficiency}

    except Exception as e:
        log_metric_error("employer_screening_efficiency", e, {"data_keys": list(data.keys()) if isinstance(data, dict) else None})
        return {}

# Metric function registry
METRIC_FUNCTIONS = {
    'average_job_seeker_experience': average_job_seeker_experience,
    'job_application_success_rate': job_application_success_rate,
    'employer_screening_efficiency': employer_screening_efficiency,
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

