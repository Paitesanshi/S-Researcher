"""
Paradigm configuration for research workflow.

Unified paradigm system based on S(M,C) ↦ O framework.

All paradigms share the same simulation process:
S(M, C) ↦ O
where:
- S: Social Simulator (Agent-based simulation)
- M: Mechanism (Agent behavior rules, theories)
- C: Configuration (Scenario parameters, conditions)
- O: Outcome (Emergent phenomena, observations)

Three unified paradigms:
1. Deductive (演绎型): M+C → O* - Hypothetico-deductive method
   - Generate multiple competing hypotheses from theory
   - Simulate each hypothesis to predict different outcomes
   - Compare simulation results to identify best-fitting hypothesis

2. Inductive (归纳型): O_real+C → M* - Direct simulation and inductive inference
   - Directly simulate observed phenomena
   - Analyze simulation results to discover patterns
   - Inductively infer underlying behavioral mechanisms

3. Abductive (溯因型): M+{C_i} → R* - Causal relationship quantification
   - Design controlled experiments with multiple condition levels
   - Systematically vary conditions to measure effects
   - Quantify causal relationships and dose-response curves
"""

from typing import Dict, List, Any

PARADIGM_CONFIGS = {
    # ========== New Unified Paradigms ==========
    "deductive": {
        "name": "Deductive (Deductive: M+C → O*)",
        "description": "Hypothetico-deductive approach: generate hypotheses from theory, then validate through simulation",
        "input_fields": ["theory", "condition"],
        "workflow": "multi_hypothesis",
        "needs_full_workflow": True,  # Generate experiment_config and intervention_specifications
        "hypothesis_count": 3,
        "profile_field": "decision_logic",
        "prompts": {
            "inspiration_system": """You are an expert social science researcher specializing in multi-agent simulations.
Based on a social science theory and specific conditions, your task is to generate 3 different hypotheses that predict different possible outcomes based on the theory.

For each hypothesis:
1. **Mutually Exclusive**: The 3 hypotheses should represent different predictions or interpretations of how the theory applies
2. **Implementable**: Must be possible to simulate through agent decision rules
3. **Verifiable**: Different hypotheses should produce observable behavioral differences

Theoretical perspective suggestions:
- Hypothesis 1: Strong effect prediction (theory applies fully under these conditions)
- Hypothesis 2: Moderate effect prediction (theory applies with some limitations)
- Hypothesis 3: Weak/no effect prediction (theory may not apply well under these conditions)

For each hypothesis, also generate a simulation scenario:
1. **Outline** the key agent types involved
2. **Describe** the basic interaction mechanisms between agents
3. **Suggest** the parameters or variables that can be manipulated
4. **Keep** the complexity manageable (maximum of 2-4 agent types)

Format your response as JSON with the following structure:
{
    "research_question": {
        "question": "Specific research question about theory validation",
        "rationale": "Why this question is important for testing the theory"
    },
    "hypotheses": [
        {
            "name": "Hypothesis name",
            "theoretical_basis": "How this prediction derives from the theory",
            "decision_logic": "Detailed Agent decision logic description including decision trigger conditions, decision rules, and parameter settings",
            "expected_outcome": "Expected macroscopic phenomenon if this hypothesis is correct",
            "key_parameters": {"param1": "value", "param2": "value"}
        },
        {
            "name": "Hypothesis 2 name",
            "theoretical_basis": "Different prediction from theory",
            "decision_logic": "Different decision logic",
            "expected_outcome": "Different expected outcome",
            "key_parameters": {"param1": "value", "param2": "value"}
        },
        {
            "name": "Hypothesis 3 name",
            "theoretical_basis": "Third prediction from theory",
            "decision_logic": "Third decision logic",
            "expected_outcome": "Third expected outcome",
            "key_parameters": {"param1": "value", "param2": "value"}
        }
    ],
    "simulation_scenario": {
        "description": "Brief description of the simulation scenario",
        "agent_types": ["List of agent types"],
        "interactions": "Description of how agents interact",
        "key_parameters": ["List of important parameters"],
        "expected_insights": "What insights might be gained from hypothesis testing"
    }
}

Be creative but realistic. Focus on hypotheses that would yield meaningful theoretical insights while being feasible to implement with language model-based agents.""",
            "inspiration_user_template": """Please generate 3 competing hypotheses and simulation scenario based on the theory and condition provided:

Theory: {theory}
Condition: {condition}

Requirements:
1. The 3 hypotheses should represent different predictions about how the theory applies
2. Each hypothesis should be specific enough to be simulated with language model-based agents
3. Different hypotheses should produce distinguishable behavioral differences
4. Consider what kinds of agent decision logic would best represent each theoretical prediction

Remember to format your response as JSON with the structure specified in your instructions.""",
            "detailer_prompt": "Please develop the following selected research question, hypotheses and simulation scenario for hypothesis testing"
        },
        "output_key": "research_questions"
    },

    "inductive": {
        "name": "Inductive (Inductive: O_real+C → M*)",
        "description": "Direct simulation and inductive inference: simulate observed phenomena, then infer underlying mechanisms",
        "input_fields": ["observation", "condition"],
        "workflow": "standard",
        "needs_experiment_config": True,  # Generate experiment_config for replication, but no interventions
        "prompts": {
            "inspiration_system": """You are an expert social science researcher specializing in multi-agent simulations.
Your task is to generate corresponding simulation scenarios based on a real social science observation and specific conditions.

For each simulation scenario:
1. **Outline** the key agent types involved.
2. **Describe** the basic interaction mechanisms between agents.
3. **Suggest** the parameters or variables that can be manipulated.
4. **Keep** the complexity manageable (maximum of 2-4 agent types).

The goal is to directly simulate the observed phenomenon, then analyze the simulation results to inductively infer the underlying behavioral mechanisms.

Please write the scenarios.
Format your response as JSON with the following structure:
{
    "simulation_scenario": {
        "description": "Brief description of the simulation scenario",
        "agent_types": ["List of agent types"],
        "interactions": "Description of how agents interact",
        "key_parameters": ["List of important parameters"],
        "expected_insights": "What mechanisms might be discovered through simulation"
    }
}

Be creative but realistic. Focus on scenarios that would yield meaningful insights while being feasible to implement with language model-based agents.""",
            "inspiration_user_template": """Please generate simulation scenarios based on the real observation and condition provided:

Observation: {observation}
Condition: {condition}

For each scenario:
1. Ensure it directly simulates the observed phenomenon
2. Consider what kinds of interactions between agents would reproduce the observation
3. Assess the complexity and feasibility of implementing the simulation
4. Focus on enabling inductive inference of mechanisms from simulation results

Remember to format your response as JSON with the structure specified in your instructions.""",
            "detailer_prompt": "Please develop the following selected simulation scenario for inductive mechanism discovery"
        },
        "output_key": "scenario"
    },

    "abductive": {
        "name": "Abductive (Abductive: M+{C_i} → R*)",
        "description": "Quantify causal relationships through experiments",
        "input_fields": ["theory", "observation", "condition"],
        "workflow": "experimental_design",
        "prompts": {
            "inspiration_system": """You are an expert social science researcher specializing in multi-agent simulations.
Your task is to generate corresponding simulation scenarios based on a social science theory, a theory-driven observation, and a specific condition. We will design controlled experiments to quantify causal relationships.

For each simulation scenario:
1. **Outline** the key agent types involved
2. **Describe** the basic interaction mechanisms between agents
3. **Suggest** the parameters or variables that can be manipulated
4. **Keep** the complexity manageable (maximum of 2-4 agent types)
5. The **independent_variable** should be the condition being manipulated
6. The **independent_variable_range** should include multiple levels (at least 5-10 values) to capture the full relationship
7. The **dependent_variable** should be the observation being measured

Please write scenarios.
Format your response as JSON with the following structure:
{
    "simulation_scenario": {
        "description": "Brief description of the simulation scenario",
        "independent_variable": "What variable will be manipulated",
        "independent_variable_range": ["List of the independent variable levels, detailed numbers"],
        "dependent_variable": "What variable will be measured",
        "control_variables": ["List of variables to be controlled"],
        "agent_types": ["List of agent types"],
        "interactions": "Description of how agents interact",
        "key_parameters": ["List of important parameters"],
        "expected_insights": "What causal relationships might be discovered",
        "replications": 50
    }
}

Be creative but realistic. Focus on scenarios that would yield meaningful causal insights while being feasible to implement with language model-based agents.""",
            "inspiration_user_template": """Please generate simulation scenarios for causal analysis based on the social science theory, observation, and condition provided:

Theory: {theory}
Observation: {observation}
Condition: {condition}

For the scenario:
1. Design an experimental manipulation of the condition variable across multiple levels
2. Ensure the design can quantify the causal effect on the observation
3. Consider what control variables need to be held constant
4. Assess the complexity and feasibility of implementing the simulation

Remember to format your response as JSON with the structure specified in your instructions.""",
            "detailer_prompt": "Please develop the following selected simulation scenario for experimental causal analysis"
        },
        "output_key": "scenario"
    },

    # ========== Legacy Paradigms (Backward Compatibility) ==========
    "theory_validation": {
        "name": "Theory Validation (T+C → O)",
        "description": "Generate observations from theory and conditions",
        "input_fields": ["theory", "condition"],
        "prompts": {
            "inspiration_system": """You are an expert social science researcher specializing in multi-agent simulations.
Your task is to generate corresponding simulation scenarios based on a social science theory and a specific condition of that theory.

For each simulation scenario:
1.  **Outline** the key agent types involved.
2.  **Describe** the basic interaction mechanisms between agents.
3.  **Suggest** the parameters or variables that can be manipulated.
4.  **Keep** the complexity manageable (maximum of 2-4 agent types).

Please write the and scenarios.
Format your response as JSON with the following structure:
{
      "simulation_scenario": {
        "description": "Brief description of the simulation scenario",
        "agent_types": ["List of agent types"],
        "interactions": "Description of how agents interact",
        "key_parameters": ["List of important parameters"],
        "expected_insights": "What insights might be gained",
      }
}

Be creative but realistic. Focus on scenarios that would yield meaningful insights while being feasible to implement with language model-based agents.""",
            "inspiration_user_template": """Please generate simulation scenarios based on the social science theory and condition provided:

Theory: {theory}
Condition: {condition}

For each research question and scenario:
1. Ensure it is specific enough to be simulated with language model-based agents.
2. Consider what kinds of interactions between agents would be most revealing.
3. Assess the complexity and feasibility of implementing the simulation.

Remember to format your response as JSON with the structure specified in your instructions.""",
            "detailer_prompt": "Please develop the following selected simulation scenario"
        },
        "output_key": "scenario"
    },

    "mechanism_discovery": {
        "name": "Mechanism Discovery (O+C → T)",
        "description": "Generate research questions from observations and conditions",
        "input_fields": ["observation", "condition"],
        "prompts": {
            "inspiration_system": """You are an expert social science researcher specializing in multi-agent simulations.
Based on a social science observation and a specific condition of the observation, your task is to generate a research question to investigate the underlying mechanisms of the observation and generate its corresponding simulation scenarios.

For each research question:
1. Focus on a specific aspect of the broader topic that would be suitable for agent-based modeling
2. Ensure the question is well-defined, specific, and can be addressed through simulation
3. Consider both theoretical relevance and practical feasibility

For each simulation scenario:
1.  **Outline** the key agent types involved.
2.  **Describe** the basic interaction mechanisms between agents.
3.  **Suggest** the parameters or variables that can be manipulated.
4.  **Keep** the complexity manageable (maximum of 2-4 agent types).

Provide a research question and scenario you think is most valuable to explore.
Format your response as JSON with the following structure:
{
  "research_questions":
    {
      "question": "Specific research question",
      "rationale": "Why this question is important and suitable for simulation",
      "simulation_scenario": {
        "description": "Brief description of the simulation scenario",
        "agent_types": ["List of agent types"],
        "interactions": "Description of how agents interact",
        "key_parameters": ["List of important parameters"],
        "expected_insights": "What insights might be gained",
      }
    }
}

Be creative but realistic. Focus on scenarios that would yield meaningful insights while being feasible to implement with language model-based agents.""",
            "inspiration_user_template": """Please generate simulation scenarios based on the social science observation and condition provided:

Observation: {observation}
Condition: {condition}

For each research question and scenario:
1. Ensure it is specific enough to be simulated with language model-based agents.
2. Consider what kinds of interactions between agents would be most revealing.
3. Assess the complexity and feasibility of implementing the simulation.

Remember to format your response as JSON with the structure specified in your instructions.""",
            "detailer_prompt": "Please develop the following selected research question and simulation scenario"
        },
        "output_key": "research_questions"
    },

    "attribution_analysis": {
        "name": "Attribution Analysis (T+O+C → C_weight)",
        "description": "Analyze condition weights from theory, observation, and conditions",
        "input_fields": ["theory", "observation", "condition"],
        "prompts": {
            "inspiration_system": """You are an expert social science researcher specializing in multi-agent simulations.
Your task is to generate corresponding simulation scenarios based on a social science theory, a theory-driven observation, and a specific condition.

For each simulation scenario:
1.  **Outline** the key agent types involved.
2.  **Describe** the basic interaction mechanisms between agents.
3.  **Suggest** the parameters or variables that can be manipulated.
4.  **Keep** the complexity manageable (maximum of 2-4 agent types).
5.  the Independent_variable should be the condition.
6.  the dependent_variable should be the observation.

Please write scenarios.
Format your response as JSON with the following structure:
{
      "simulation_scenario": {
        "description": "Brief description of the simulation scenario",
        "Independent_variable" : "What variable will be manipulated",
        "Independent_variable_range": "[List of the independent variable, detail numbers]",
        "dependent_variable": "What variable will be measured",
        "agent_types": ["List of agent types"],
        "interactions": "Description of how agents interact",
        "key_parameters": ["List of important parameters"],
        "expected_insights": "What insights might be gained",
      }
}
Be creative but realistic. Focus on scenarios that would yield meaningful insights while being feasible to implement with language model-based agents.""",
            "inspiration_user_template": """Please generate simulation scenarios based on the social science theory, social science observation, and condition provided:
Theory: {theory}
Observation: {observation}
Condition: {condition}

For each research question and scenario:
1. Ensure it is specific enough to be simulated with language model-based agents.
2. Consider what kinds of interactions between agents would be most revealing.
3. Assess the complexity and feasibility of implementing the simulation.

Remember to format your response as JSON with the structure specified in your instructions.""",
            "detailer_prompt": "Please develop the following selected simulation scenario"
        },
        "output_key": "scenario"
    },

    "boundary_exploration": {
        "name": "Boundary Exploration (T+O+C → C_boundary)",
        "description": "Explore condition boundaries from theory, observation, and conditions",
        "input_fields": ["theory", "observation", "condition"],
        "prompts": {
            "inspiration_system": """You are an expert social science researcher specializing in multi-agent simulations.
Your task is to generate corresponding simulation scenarios based on a social science theory, a theory-driven observation, and a specific condition. We will explore the boundaries of this condition.
For each simulation scenario:
1.  **Outline** the key agent types involved.
2.  **Describe** the basic interaction mechanisms between agents.
3.  **Suggest** the parameters or variables that can be manipulated.
4.  **Keep** the complexity manageable (a maximum of 2-4 agent types).
5.  The independent variable's range should be the condition's boundary (both inside and outside the left and right boundaries).
6.  The **dependent variable** should be the observation.

Please write the research questions and scenarios.
Format your response as JSON with the following structure:
{
      "simulation_scenario": {
        "description": "Brief description of the simulation scenario",
        "Independent_variable" : "What variable will be manipulated",
        "Independent_variable_range": "[List of the independent variable, detail numbers]",
        "dependent_variable": "What variable will be measured",
        "agent_types": ["List of agent types"],
        "interactions": "Description of how agents interact",
        "key_parameters": ["List of important parameters"],
        "expected_insights": "What insights might be gained",
      }
}
Be creative but realistic. Focus on scenarios that would yield meaningful insights while being feasible to implement with language model-based agents.""",
            "inspiration_user_template": """Please generate simulation scenarios based on the social science theory, social science observation, and condition provided:
Theory: {theory}
Observation: {observation}
Condition: {condition}

For each research question and scenario:
1. Ensure it is specific enough to be simulated with language model-based agents.
2. Consider what kinds of interactions between agents would be most revealing.
3. Assess the complexity and feasibility of implementing the simulation.

Remember to format your response as JSON with the structure specified in your instructions.""",
            "detailer_prompt": "Please develop the following selected simulation scenario"
        },
        "output_key": "scenario"
    }
}


def get_paradigm_config(paradigm_key: str) -> Dict[str, Any]:
    """
    Get configuration for a specific paradigm.

    Args:
        paradigm_key: Key of the paradigm (e.g., 'deductive', 'inductive', 'abductive')

    Returns:
        Dictionary containing paradigm configuration

    Raises:
        ValueError: If paradigm_key is not found
    """
    if paradigm_key not in PARADIGM_CONFIGS:
        available = ", ".join(PARADIGM_CONFIGS.keys())
        raise ValueError(f"Unknown paradigm: {paradigm_key}. Available: {available}")
    return PARADIGM_CONFIGS[paradigm_key]


def list_paradigms() -> List[str]:
    """
    List all available paradigm keys.

    Returns:
        List of paradigm keys
    """
    return list(PARADIGM_CONFIGS.keys())


def validate_input(paradigm_key: str, input_data: Dict[str, Any]) -> None:
    """
    Validate that input_data contains all required fields for the paradigm.

    Args:
        paradigm_key: Key of the paradigm
        input_data: Input data dictionary to validate

    Raises:
        ValueError: If required fields are missing
    """
    config = get_paradigm_config(paradigm_key)
    required_fields = config["input_fields"]
    missing_fields = [field for field in required_fields if not input_data.get(field)]

    if missing_fields:
        raise ValueError(
            f"Paradigm '{paradigm_key}' requires {required_fields}, "
            f"but missing: {missing_fields}"
        )
