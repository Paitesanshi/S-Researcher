"""
Experiment Agent for generating structured simulation experiment configurations.

This module provides the ExperimentAgent class, which is responsible for generating
structured experiment configurations including scenarios, and analysis
plans based on research questions and scene information.
"""

import json
from typing import Dict, Any

from .agent_base import AgentBase


class Experimentagent(AgentBase):
    """
    Agent responsible for generating simulation experiment configurations.
    
    The experiment agent takes a research question and scene information to generate
    a structured experiment configuration that includes scenarios,
    metrics, and analysis settings following a predefined JSON schema.
    
    Attributes:
        model_config (str): Configuration name for the underlying language model
    """
    
    def __init__(self, model_config=None):
        """
        Initialize the experiment agent with specified model configuration.
        
        Args:
            model_config (str, optional): The model configuration name to use.
                If None, the default model will be used.
        """
        super().__init__("Experiment Agent", model_config)
        self.tool_list = [
                          "independent_t_test",
                          "paired_t_test",
                          "mann_whitney_u_test",
                          "wilcoxon_test",
                          "one_way_anova",
                          "kruskal_wallis_test",
                          "chi2_independence_test",
                          "fisher_exact_test",
                          "ks_2samp_test",
                          
                          "granger_causality",
                          "var_model",
                          "time_series_correlation",
                          "compute_trend",
                          
                          "bayes_factor_ttest",
                          "bayesian_simple_regression",
                          "bayesian_hierarchical_regression",
                          
                          "fit_mixedlm",
                          
                          "factorial_anova",
                          "manova",
                          
                          "repeated_measures_anova",
                          "friedman_test",
                          "ancova",
                          "multiple_comparisons"
                      ]
    
    def _construct_system_prompt(self) -> str:
        """
        Construct the system prompt defining the agent's role and task requirements.
        
        Returns:
            str: System prompt with detailed instructions for experiment configuration generation
        """
        return """You are an expert social science researcher specializing in multi-agent simulations.
Your task is to design an experiment based on the research question and corresponding scene information.
Focus on EXPERIMENTAL DESIGN rather than simulation configuration details.

1. **experiment_info**: Basic experiment information including name, title, description, research question, and creation date.
2. **scene_reference**: Reference to the scene (NOT detailed simulation configuration) - use scene_name consistently.
3. **experimental_design**: Design experimental groups including control groups, treatment groups, and replication_settings based on research variables.
4. **replication_settings**: Configure how many times each experiment should be replicated for statistical validity. Default num_replicates is 3.
5. **analysis_config**: Statistical analysis configuration including tests, confidence level, and comparison groups.

IMPORTANT: Do NOT include detailed simulation parameters (agent counts, steps, etc.) - these belong in scenario_config.json.
Format your response as JSON with the following structure:
{
  "experiment_info": {
    "name": "communication_effectiveness_study",
    "title": "Communication Effectiveness in Property Rights",
    "description": "Study on how communication affects property rights establishment",
    "research_question": "How does communication effectiveness impact property rights establishment?",
    "created_date": "2025-08-10"
  },
  "scene_reference": {
    "scene_name": "mining_property_rights",
    "scene_path": "src/envs/mining_property_rights"
  },
  "experimental_groups": {
    "control_group": {
      "name": "control_group_001",
      "description": "Baseline scenario without interventions",
      "parameters": {
        "random_seed": 12345
      }
    },
    "treatment_groups": [
      {
        "name": "treatment_group_001",
        "description": "Enhanced cultural openness intervention - adds new cultural traits",
        "parameters": {
          "random_seed": 12345
        }
      },
      {
        "name": "treatment_group_002",
        "description": "Social connector enhancement - targets social personality agents",
        "parameters": {
          "random_seed": 12345
        }
      },
      ...
    ],
    "replication_settings": {
      "num_replicates": 3,
      "base_seed": 10001,
      "seed_strategy": "sequential"
    }
  },
  "analysis_config": {
    "statistical_tests": ["t_test", "anova",...],
    "confidence_level": 0.95,
    "comparison_groups": [
      {
        "name": "control_vs_treatment1",
        "groups": ["control_group_001", "treatment_group_001"]
      }
      ...
    ]
  }
}
Note that the JSON you generate must not contain any comments.
Please note that the above JSON structure is just an example and has no relation to the content you are to generate. You need to create the corresponding experimental configuration based on the research question and scenario information.
"""

    def _construct_system_prompt_no_intervention(self) -> str:
        """
        Construct the system prompt for experiments without interventions (inductive paradigm).

        Returns:
            str: System prompt for no-intervention experiment configuration
        """
        return """You are an expert social science researcher specializing in multi-agent simulations.
Your task is to design an experiment configuration for INDUCTIVE research - observing and analyzing simulation results WITHOUT experimental interventions.

This is for mechanism discovery: we run the simulation multiple times to collect data and inductively infer underlying mechanisms from the observed patterns.

1. **experiment_info**: Basic experiment information including name, title, description, research question, and creation date.
2. **scene_reference**: Reference to the scene - use scene_name consistently.
3. **experimental_groups**: For inductive research, we only have observation runs (no control/treatment distinction).
4. **replication_settings**: Configure how many times the simulation should be replicated for statistical validity. Default num_replicates is 3.
5. **analysis_config**: Statistical analysis configuration for pattern discovery and mechanism inference.

IMPORTANT:
- NO treatment_groups or control_group needed - this is observational research
- Focus on replication_settings for running multiple simulations
- Analysis should focus on pattern discovery, not group comparisons

Format your response as JSON with the following structure:
{
  "experiment_info": {
    "name": "mechanism_discovery_study",
    "title": "Mechanism Discovery Study",
    "description": "Inductive study to discover underlying mechanisms through simulation observation",
    "research_question": "What mechanisms drive the observed phenomena?",
    "created_date": "2025-08-10"
  },
  "scene_reference": {
    "scene_name": "scenario_name",
    "scene_path": "src/envs/scenario_name"
  },
  "experimental_groups": {
    "observation_runs": {
      "name": "observation_run",
      "description": "Baseline simulation runs for mechanism discovery",
      "parameters": {
        "random_seed": 10001
      }
    },
    "replication_settings": {
      "num_replicates": 3,
      "base_seed": 10001,
      "seed_strategy": "sequential"
    }
  },
  "analysis_config": {
    "statistical_tests": ["descriptive_statistics", "correlation_analysis", "time_series_analysis"],
    "confidence_level": 0.95,
    "analysis_focus": [
      {
        "name": "pattern_discovery",
        "description": "Identify recurring patterns in agent behaviors"
      },
      {
        "name": "mechanism_inference",
        "description": "Infer underlying behavioral mechanisms from observed patterns"
      }
    ]
  }
}
Note that the JSON you generate must not contain any comments.
"""

    def _construct_user_prompt(self, research_question: str, scene_information: str, scene_name: str) -> str:
        """
        Construct the user prompt with specific research question and scene information.
        
        Args:
            research_question (str): Specific research question to base the experiment on
            scene_information (str): Contextual information about the simulation scenario
            
        Returns:
            str: Formatted user prompt with input parameters
        """
        return f"""Please generate an experiment configuration based on the research question and scene information.
For **statistical_tests**, the tools you can use are **{self.tool_list}**.

IMPORTANT: Use scene_name: "{scene_name}" in the scene_reference section.
Focus on experimental design, NOT simulation configuration details.

research question: {research_question}
scene information: {scene_information}
scene_name: {scene_name}

Remember to format your response as JSON with the structure specified in your instructions."""
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input data to generate structured experiment configuration.

        Args:
            input_data (Dict[str, Any]): Dictionary containing:
                - research_question (str): Specific research question
                - scene_information (str): Contextual scene information
                - scene_name (str): Name of the scene
                - no_intervention (bool, optional): If True, generate config without interventions (inductive paradigm)

        Returns:
            Dict[str, Any]: Dictionary containing generated experiments_config

        Raises:
            ValueError: If required input fields are missing or JSON parsing fails
        """
        # Extract required parameters from input
        research_question = input_data.get("research_question", "")
        scene_information = input_data.get("scene_information", "")
        scene_name = input_data.get("scene_name", "")
        no_intervention = input_data.get("no_intervention", False)

        if not scene_information or not research_question or not scene_name:
            raise ValueError("research_question, scene_information, and scene_name are all required.")

        # Construct prompts for LLM interaction
        # Use different prompt for no-intervention experiments (inductive paradigm)
        if no_intervention:
            system_prompt = self._construct_system_prompt_no_intervention()
        else:
            system_prompt = self._construct_system_prompt()
        user_prompt = self._construct_user_prompt(research_question, scene_information, scene_name)

        # Debug output for prompt inspection
        
        # Generate response using configured model
        response = self.generate_response(system_prompt, user_prompt)
        print("Response from EXP Agent:")
        print(response)
        print("=" * 20)
        
        # Attempt to parse JSON response with fallback strategies
        try:
            parsed_response = json.loads(response)
            return parsed_response
        except json.JSONDecodeError:
            # Try alternative JSON extraction methods
            try:
                # Extract from code block formatting
                if "```json" in response:
                    json_content = response.split("```json")[1].split("```")[0].strip()
                elif "```" in response:
                    json_content = response.split("```")[1].strip()
                else:
                    json_content = response
                
                parsed_response = json.loads(json_content)
                return parsed_response
            except (json.JSONDecodeError, IndexError):
                # Final failure case with error message
                raise ValueError(f"Failed to parse agent response as JSON. Response: {response[:200]}...")