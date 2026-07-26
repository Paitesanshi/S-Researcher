"""
Unified ParadigmAgent for all research paradigms.

Configuration-driven implementation supporting all research paradigms through
a single, clean interface.
"""

import json
from typing import Dict, Any
from loguru import logger

from .inspiration_agent import InspirationAgent
from .detailer_agent import DetailerAgent
from .experiments_agent import Experimentagent
from .intervention_agent import InterventionAgent
from .scenario_agent import ScenarioAgent
from .paradigm_config import get_paradigm_config, validate_input


class ParadigmAgent:
    """
    Unified agent manager for all research paradigms.

    Manages workflow between InspirationAgent and DetailerAgent based on
    paradigm configuration. Uses semantic naming for clarity.

    For paradigms requiring full experimental workflow (deductive with multi-hypothesis, abductive),
    also manages ExperimentAgent, InterventionAgent, and ScenarioAgent.
    """

    def __init__(self, model_name: str, paradigm_name: str = "deductive"):
        """
        Initialize the paradigm agent.

        Args:
            model_name: Model configuration name to use.
            paradigm_name: Research paradigm (e.g., 'deductive', 'inductive', 'abductive').
        """
        self.paradigm_name = paradigm_name
        self.config = get_paradigm_config(paradigm_name)
        self.model_name = model_name

        # Initialize core agents
        self.inspiration_agent = InspirationAgent(model_name, paradigm_name)
        self.detailer_agent = DetailerAgent(model_name, paradigm_name)

        # Initialize experimental agents for paradigms that need full workflow
        # Check both legacy hardcoded list (for backward compatibility) and new config-driven approach
        legacy_full_workflow = paradigm_name in ["attribution_analysis", "boundary_exploration"]
        self.needs_full_workflow = (
            legacy_full_workflow or
            self.config.get("needs_full_workflow", False)
        )
        # Check if paradigm needs experiment config only (no interventions), e.g., inductive
        self.needs_experiment_config = self.config.get("needs_experiment_config", False)

        if self.needs_full_workflow:
            self.experiment_agent = Experimentagent(model_name)
            self.intervention_agent = InterventionAgent(model_name)
            self.scenario_agent = ScenarioAgent(model_name)
            logger.info(f"Initialized full experimental workflow for paradigm: {self.config['name']}")
        elif self.needs_experiment_config:
            # For inductive paradigm: only need experiment agent for replication settings
            self.experiment_agent = Experimentagent(model_name)
            self.scenario_agent = ScenarioAgent(model_name)
            logger.info(f"Initialized experiment config workflow (no interventions) for paradigm: {self.config['name']}")
        else:
            logger.info(f"Initialized basic workflow for paradigm: {self.config['name']}")

    def run(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the paradigm workflow.

        For basic paradigms:
            inspiration → detailer → Returns: {inspiration, odd}

        For experiment-config-only paradigms (inductive):
            inspiration → detailer → experiment → scenario
            → Returns: {inspiration, odd, experiment, scenario}

        For full workflow paradigms (deductive with multi-hypothesis, abductive):
            inspiration → detailer → experiment → intervention → scenario
            → Returns: {inspiration, odd, experiment, intervention, scenario}

        Args:
            user_input: Input data containing paradigm-specific fields.

        Returns:
            Dictionary containing workflow outputs:
            - inspiration_output: Research questions and scenarios
            - odd_output: ODD protocol
            - experiment_output: (for experiment-config and full workflow) Experiment configuration
            - intervention_output: (only for full workflow) Intervention specifications
            - scenario_output: (for experiment-config and full workflow) Scenario configuration

        Raises:
            ValueError: If required input fields are missing.
        """
        if self.needs_full_workflow:
            total_steps = 5
        elif self.needs_experiment_config:
            total_steps = 4  # inspiration → detailer → experiment → scenario (no intervention)
        else:
            total_steps = 2
        logger.info(f"\n[Step 1/{total_steps}] Generating research questions and scenarios ({self.config['name']})...")

        # Validate input has required fields for this paradigm
        validate_input(self.paradigm_name, user_input)

        # Extract only the fields needed for this paradigm
        inspiration_input = {
            field: user_input.get(field)
            for field in self.config["input_fields"]
        }

        # Run inspiration agent
        inspiration_output = self.inspiration_agent.process(inspiration_input)

        logger.info(f"\n[Step 2/{total_steps}] Elaborating scenario into ODD protocol...")

        # Transform inspiration output to detailer input format
        detailer_input = {
            "selected_scenario_details": inspiration_output.get(self.config["output_key"], {}),
            "evaluations": [],  # No evaluations in simplified workflow
            "original_topic": inspiration_output.get("input_data", {}).get("theory", "") or
                             inspiration_output.get("input_data", {}).get("observation", "")
        }

        # Run detailer agent with transformed input
        odd_output = self.detailer_agent.process(detailer_input)

        # Build base result
        result = {
            "inspiration_output": inspiration_output,
            "odd_output": odd_output
        }

        # If full workflow is needed, continue with experiment → intervention → scenario
        if self.needs_full_workflow:
            # Extract research question and scene information from odd_output
            research_question = odd_output.get("research_question", "") or detailer_input.get("original_topic", "")

            # Get scene information from ODD protocol's overview section
            odd_protocol = odd_output.get("odd_protocol", {})
            overview = odd_protocol.get("overview", {})
            scene_information = overview.get("system_goal", "") or overview.get("environment_description", "")

            # Get scene_name from odd_output (detailer already generates this)
            scene_name = odd_output.get("scene_name", "") or user_input.get("scene_name", "")

            # If still no scene_name, generate from description
            if not scene_name:
                description = inspiration_output.get(self.config["output_key"], {}).get("description", "scenario")
                scene_name = description.replace(" ", "_").replace("/", "_").replace("\\", "_")[:50]

            # Validate we have all required fields
            if not research_question:
                logger.warning("research_question is empty, using fallback")
                research_question = f"Research on {scene_name}"
            if not scene_information:
                logger.warning("scene_information is empty, using fallback")
                scene_information = f"Multi-agent simulation for {scene_name}"
            if not scene_name:
                logger.warning("scene_name is empty, using fallback")
                scene_name = "default_scenario"

            logger.info(f"\n[Step 3/{total_steps}] Generating experiment configuration...")
            logger.debug(f"research_question: {research_question[:100]}...")
            logger.debug(f"scene_information: {scene_information[:100]}...")
            logger.debug(f"scene_name: {scene_name}")
            experiment_input = {
                "research_question": research_question,
                "scene_information": scene_information,
                "scene_name": scene_name
            }
            experiment_output = self.experiment_agent.process(experiment_input)

            logger.info(f"\n[Step 4/{total_steps}] Generating intervention specifications...")
            intervention_input = {
                "research_question": research_question,
                "exp_config": json.dumps(experiment_output, ensure_ascii=False),
                "scene_information": scene_information
            }
            intervention_output = self.intervention_agent.process(intervention_input)

            logger.info(f"\n[Step 5/{total_steps}] Generating scenario configuration...")
            scenario_input = {
                "research_question": research_question,
                "scene_information": scene_information,
                "exp_config": json.dumps(experiment_output, ensure_ascii=False),
                "scene_name": scene_name
            }
            scenario_output = self.scenario_agent.process(scenario_input)

            # Add full workflow outputs to result
            result["experiment_output"] = experiment_output
            result["intervention_output"] = intervention_output
            result["scenario_output"] = scenario_output

        # If experiment config only (inductive paradigm): experiment → scenario (no intervention)
        elif self.needs_experiment_config:
            # Extract research question and scene information from odd_output
            research_question = odd_output.get("research_question", "") or detailer_input.get("original_topic", "")

            # Get scene information from ODD protocol's overview section
            odd_protocol = odd_output.get("odd_protocol", {})
            overview = odd_protocol.get("overview", {})
            scene_information = overview.get("system_goal", "") or overview.get("environment_description", "")

            # Get scene_name from odd_output
            scene_name = odd_output.get("scene_name", "") or user_input.get("scene_name", "")

            # If still no scene_name, generate from description
            if not scene_name:
                description = inspiration_output.get(self.config["output_key"], {}).get("description", "scenario")
                scene_name = description.replace(" ", "_").replace("/", "_").replace("\\", "_")[:50]

            # Validate we have all required fields
            if not research_question:
                logger.warning("research_question is empty, using fallback")
                research_question = f"Research on {scene_name}"
            if not scene_information:
                logger.warning("scene_information is empty, using fallback")
                scene_information = f"Multi-agent simulation for {scene_name}"
            if not scene_name:
                logger.warning("scene_name is empty, using fallback")
                scene_name = "default_scenario"

            logger.info(f"\n[Step 3/{total_steps}] Generating experiment configuration (no interventions)...")
            experiment_input = {
                "research_question": research_question,
                "scene_information": scene_information,
                "scene_name": scene_name,
                "no_intervention": True  # Signal to experiment agent: generate config without treatment groups
            }
            experiment_output = self.experiment_agent.process(experiment_input)

            logger.info(f"\n[Step 4/{total_steps}] Generating scenario configuration...")
            scenario_input = {
                "research_question": research_question,
                "scene_information": scene_information,
                "exp_config": json.dumps(experiment_output, ensure_ascii=False),
                "scene_name": scene_name
            }
            scenario_output = self.scenario_agent.process(scenario_input)

            # Add experiment config outputs to result (no intervention_output)
            result["experiment_output"] = experiment_output
            result["scenario_output"] = scenario_output

        return result


# ========== New Unified Paradigm Aliases ==========
class DeductiveAgent(ParadigmAgent):
    """Deductive paradigm: M+C → O* (Hypothetico-deductive method)."""
    def __init__(self, model_name: str):
        super().__init__(model_name, "deductive")


class InductiveAgent(ParadigmAgent):
    """Inductive paradigm: O_real+C → M* (Direct simulation and inference)."""
    def __init__(self, model_name: str):
        super().__init__(model_name, "inductive")


class AbductiveAgent(ParadigmAgent):
    """Abductive paradigm: M+{C_i} → R* (Causal relationship quantification)."""
    def __init__(self, model_name: str):
        super().__init__(model_name, "abductive")


# ========== Legacy Paradigm Aliases (Backward Compatibility) ==========
class TheoryValidationAgent(ParadigmAgent):
    """LEGACY: Theory Validation paradigm → migrates to DeductiveAgent."""
    def __init__(self, model_name: str):
        logger.warning("TheoryValidationAgent is legacy, auto-migrating to 'deductive' paradigm")
        super().__init__(model_name, "theory_validation")


class MechanismDiscoveryAgent(ParadigmAgent):
    """LEGACY: Mechanism Discovery paradigm → migrates to InductiveAgent."""
    def __init__(self, model_name: str):
        logger.warning("MechanismDiscoveryAgent is legacy, auto-migrating to 'inductive' paradigm")
        super().__init__(model_name, "mechanism_discovery")


class AttributionAnalysisAgent(ParadigmAgent):
    """LEGACY: Attribution Analysis paradigm → migrates to AbductiveAgent."""
    def __init__(self, model_name: str):
        logger.warning("AttributionAnalysisAgent is legacy, auto-migrating to 'abductive' paradigm")
        super().__init__(model_name, "attribution_analysis")


class BoundaryExplorationAgent(ParadigmAgent):
    """LEGACY: Boundary Exploration paradigm → migrates to AbductiveAgent."""
    def __init__(self, model_name: str):
        logger.warning("BoundaryExplorationAgent is legacy, auto-migrating to 'abductive' paradigm")
        super().__init__(model_name, "boundary_exploration")


# Deprecated: Old naming for backward compatibility
class Paradigm1Agent(TheoryValidationAgent):
    """Deprecated: Use TheoryValidationAgent instead."""
    def __init__(self, model_name: str):
        logger.warning("Paradigm1Agent is deprecated, use TheoryValidationAgent instead")
        super().__init__(model_name)


class Paradigm2Agent(MechanismDiscoveryAgent):
    """Deprecated: Use MechanismDiscoveryAgent instead."""
    def __init__(self, model_name: str):
        logger.warning("Paradigm2Agent is deprecated, use MechanismDiscoveryAgent instead")
        super().__init__(model_name)


class Paradigm3Agent(AttributionAnalysisAgent):
    """Deprecated: Use AttributionAnalysisAgent instead."""
    def __init__(self, model_name: str):
        logger.warning("Paradigm3Agent is deprecated, use AttributionAnalysisAgent instead")
        super().__init__(model_name)


class Paradigm4Agent(BoundaryExplorationAgent):
    """Deprecated: Use BoundaryExplorationAgent instead."""
    def __init__(self, model_name: str):
        logger.warning("Paradigm4Agent is deprecated, use BoundaryExplorationAgent instead")
        super().__init__(model_name)
