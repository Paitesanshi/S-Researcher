#!/usr/bin/env python3
"""
Parameter Generator for Research Environment Design

This module provides utilities to auto-generate missing research parameters
(theory, observation, condition) based on research paradigm requirements:

New Unified Paradigms:
- DEDUCTIVE: M+C → O* (needs Theory + Condition) - Hypothetico-deductive method
- INDUCTIVE: O_real+C → M* (needs Observation + Condition) - Direct simulation inference
- ABDUCTIVE: M+{C_i} → R* (needs Theory + Observation + Condition) - Causal quantification

Legacy Paradigms (backward compatibility):
- THEORY_VALIDATION → DEDUCTIVE
- MECHANISM_DISCOVERY → INDUCTIVE
- ATTRIBUTION_ANALYSIS → ABDUCTIVE
- BOUNDARY_EXPLORATION → ABDUCTIVE
"""

from typing import Dict, Optional
from loguru import logger
from onesim.models import get_model, SystemMessage, UserMessage


class ParameterGenerator:
    """
    Generates missing research parameters for different research paradigms
    based on scenario_description and research_question.
    """

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the parameter generator.

        Args:
            model_name: Model configuration name to use for generation
        """
        self.model_name = model_name
        self.model = get_model(config_name=model_name)

    def generate_missing_parameters(
        self,
        research_paradigm: str,
        scenario_description: Optional[str] = None,
        research_question: Optional[str] = None,
        theory: Optional[str] = None,
        observation: Optional[str] = None,
        condition: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate missing parameters based on research paradigm requirements.

        Args:
            research_paradigm: The research paradigm type
            scenario_description: Description of the scenario
            research_question: The research question
            theory: Existing theory (if provided)
            observation: Existing observation (if provided)
            condition: Existing condition (if provided)

        Returns:
            Dict containing all required parameters for the paradigm
        """
        logger.info(f"Generating missing parameters for paradigm: '{research_paradigm}'")

        # Build context from available information
        context = self._build_context(scenario_description, research_question)

        # Generate parameters based on paradigm requirements
        # Support both new unified paradigms and legacy paradigms (backward compatibility)

        # New unified paradigms
        if research_paradigm == "deductive":
            # M+C → O*: needs Theory + Condition (hypothetico-deductive)
            return self._generate_for_theory_validation(context, theory, condition)
        elif research_paradigm == "inductive":
            # O_real+C → M*: needs Observation + Condition (direct simulation inference)
            return self._generate_for_mechanism_discovery(context, observation, condition)
        elif research_paradigm == "abductive":
            # M+{C_i} → R*: needs Theory + Observation + Condition (causal quantification)
            return self._generate_for_attribution_analysis(context, theory, observation, condition)

        # Legacy paradigms (backward compatibility)
        elif research_paradigm == "theory_validation":
            # Legacy: T+C → O (maps to deductive)
            return self._generate_for_theory_validation(context, theory, condition)
        elif research_paradigm == "mechanism_discovery":
            # Legacy: O+C → T (maps to inductive)
            return self._generate_for_mechanism_discovery(context, observation, condition)
        elif research_paradigm == "attribution_analysis":
            # Legacy: T+O+C → C_weight (maps to abductive)
            return self._generate_for_attribution_analysis(context, theory, observation, condition)
        elif research_paradigm == "boundary_exploration":
            # Legacy: T+O+C → C_boundary (maps to abductive)
            return self._generate_for_boundary_exploration(context, theory, observation, condition)
        else:
            # Default/auto paradigm - flexible parameters
            return self._generate_for_auto_agent(context, theory, observation, condition)

    def _build_context(self, scenario_description: Optional[str], research_question: Optional[str]) -> str:
        """Build research context from available inputs."""
        context_parts = []

        if scenario_description:
            context_parts.append(f"Research Scenario: {scenario_description}")

        if research_question:
            context_parts.append(f"Research Question: {research_question}")

        return "\n".join(context_parts) if context_parts else "No specific research background provided"

    def _generate_for_theory_validation(self, context: str, theory: Optional[str], condition: Optional[str]) -> Dict[str, str]:
        """
        Theory Validation Paradigm (T+C → O): requires Theory and Condition as inputs
        """
        result = {}

        # Generate Theory if missing
        if not theory:
            theory_prompt = f"""
Based on the following research background, please extract or generate a social science theory that needs validation:

{context}

Requirements:
1. The theory must clearly describe causal relationships between variables
2. The theory should be verifiable through simulation
3. The theory should be closely related to the research scenario
4. Express in concise and clear language

Please provide the theory statement directly:
"""
            result['theory'] = self._call_model(theory_prompt)
        else:
            result['theory'] = theory

        # Generate Condition if missing
        if not condition:
            condition_prompt = f"""
Based on the following research background and theory, please generate the condition settings required for theory validation:

{context}

Theory: {result['theory']}

Requirements:
1. Conditions should clearly specify the context and scope where the theory applies
2. Conditions should include key environmental assumptions
3. Conditions should be achievable in simulation
4. Express in clear and specific language

Please provide the condition description directly:
"""
            result['condition'] = self._call_model(condition_prompt)
        else:
            result['condition'] = condition

        logger.info(f"✓ Theory validation paradigm parameters generated: Theory={'provided' if theory else 'generated'}, Condition={'provided' if condition else 'generated'}")
        return result

    def _generate_for_mechanism_discovery(self, context: str, observation: Optional[str], condition: Optional[str]) -> Dict[str, str]:
        """
        Mechanism Discovery Paradigm (O+C → T): requires Observation and Condition as inputs
        """
        result = {}

        # Generate Observation if missing
        if not observation:
            observation_prompt = f"""
Based on the following research background, please describe a phenomenon or observation that requires mechanism explanation:

{context}

Requirements:
1. The observation should describe specific behavioral patterns or phenomena
2. The observation should include puzzling or unexplained aspects
3. The observation should be objective and measurable
4. Express in clear and specific language

Please provide the observation phenomenon description directly:
"""
            result['observation'] = self._call_model(observation_prompt)
        else:
            result['observation'] = observation

        # Generate Condition if missing
        if not condition:
            condition_prompt = f"""
Based on the following research background and observed phenomenon, please generate the condition settings required for mechanism discovery:

{context}

Observed Phenomenon: {result['observation']}

Requirements:
1. Conditions should describe the environment and context where the phenomenon occurs
2. Conditions should include key factors that influence the mechanism
3. Conditions should be controllable in simulation
4. Express in clear and specific language

Please provide the condition description directly:
"""
            result['condition'] = self._call_model(condition_prompt)
        else:
            result['condition'] = condition

        logger.info(f"✓ Mechanism discovery paradigm parameters generated: Observation={'provided' if observation else 'generated'}, Condition={'provided' if condition else 'generated'}")
        return result

    def _generate_for_attribution_analysis(self, context: str, theory: Optional[str], observation: Optional[str], condition: Optional[str] = None) -> Dict[str, str]:
        """
        Attribution Analysis Paradigm (T+O+C → C_weight): requires Theory, Observation, and Condition as inputs
        """
        result = {}

        # Generate Theory if missing
        if not theory:
            theory_prompt = f"""
Based on the following research background, please generate a theoretical framework about multi-factor influences:

{context}

Requirements:
1. The theory should describe how multiple factors influence outcomes
2. The theory should include interactions between factors
3. The theory should be quantifiable for analysis
4. Express in clear and specific language

Please provide the theory description directly:
"""
            result['theory'] = self._call_model(theory_prompt)
        else:
            result['theory'] = theory

        # Generate Observation if missing
        if not observation:
            observation_prompt = f"""
Based on the following research background, please describe a phenomenon that requires attribution analysis:

{context}

Theoretical Framework: {result['theory']}

Requirements:
1. The observation should describe specific results or behavioral patterns
2. The observation should suggest multiple potential influencing factors
3. The observation should be quantifiable and measurable
4. Express in clear and specific language

Please provide the observed phenomenon description directly:
"""
            result['observation'] = self._call_model(observation_prompt)
        else:
            result['observation'] = observation

        # Generate Condition if missing
        if not condition:
            condition_prompt = f"""
Based on the following research background, theory, and observation, please generate the condition settings for attribution analysis:

{context}

Theory: {result['theory']}
Observation: {result['observation']}

Requirements:
1. Conditions should describe the contextual factors that may influence the attribution weights
2. Conditions should be manipulable variables that can be systematically varied
3. Conditions should be clearly defined and measurable
4. Express in clear and specific language

Please provide the condition description directly:
"""
            result['condition'] = self._call_model(condition_prompt)
        else:
            result['condition'] = condition

        logger.info(f"✓ Attribution analysis paradigm parameters generated: Theory={'provided' if theory else 'generated'}, Observation={'provided' if observation else 'generated'}, Condition={'provided' if condition else 'generated'}")
        return result

    def _generate_for_boundary_exploration(self, context: str, theory: Optional[str], observation: Optional[str], condition: Optional[str] = None) -> Dict[str, str]:
        """
        Boundary Exploration Paradigm (T+O+C → C_boundary): requires Theory, Observation, and Condition as inputs
        """
        result = {}

        # Generate Theory if missing
        if not theory:
            theory_prompt = f"""
Based on the following research background, please generate a theory that requires boundary condition exploration:

{context}

Requirements:
1. The theory should describe patterns that hold under specific conditions
2. The theory should suggest the existence of applicable boundaries and limitations
3. The theory should include variable parameters
4. Express in clear and specific language

Please provide the theory description directly:
"""
            result['theory'] = self._call_model(theory_prompt)
        else:
            result['theory'] = theory

        # Generate Observation if missing
        if not observation:
            observation_prompt = f"""
Based on the following research background, please describe a phenomenon that requires boundary exploration:

{context}

Theory: {result['theory']}

Requirements:
1. The observation should describe phenomena that change under different conditions
2. The observation should suggest the existence of critical points or turning points
3. The observation should have parameter dependencies
4. Express in clear and specific language

Please provide the observed phenomenon description directly:
"""
            result['observation'] = self._call_model(observation_prompt)
        else:
            result['observation'] = observation

        # Generate Condition if missing
        if not condition:
            condition_prompt = f"""
Based on the following research background, theory, and observation, please generate the condition settings for boundary exploration:

{context}

Theory: {result['theory']}
Observation: {result['observation']}

Requirements:
1. Conditions should describe the range of contextual parameters to be explored
2. Conditions should specify the critical variables that define theory boundaries
3. Conditions should enable systematic variation to find boundary limits
4. Express in clear and specific language

Please provide the condition description directly:
"""
            result['condition'] = self._call_model(condition_prompt)
        else:
            result['condition'] = condition

        logger.info(f"✓ Boundary exploration paradigm parameters generated: Theory={'provided' if theory else 'generated'}, Observation={'provided' if observation else 'generated'}, Condition={'provided' if condition else 'generated'}")
        return result

    def _generate_for_auto_agent(self, context: str, theory: Optional[str], observation: Optional[str], condition: Optional[str]) -> Dict[str, str]:
        """
        Auto Agent Paradigm: flexible parameter generation
        """
        result = {}

        # Generate any missing parameters with flexible approach
        if not theory:
            theory_prompt = f"""
Based on the following research background, please generate relevant theoretical framework or hypothesis:

{context}

Requirements:
1. The theory should be closely related to the research background
2. The theory should be verifiable
3. The theory should have practical significance
4. Express in clear and specific language

Please provide the theory description directly:
"""
            result['theory'] = self._call_model(theory_prompt)
        else:
            result['theory'] = theory

        if not observation:
            observation_prompt = f"""
Based on the following research background, please describe relevant phenomena or observations:

{context}

Requirements:
1. The observation should describe specific behaviors or phenomena
2. The observation should be related to the research question
3. The observation should be measurable
4. Express in clear and specific language

Please provide the observation description directly:
"""
            result['observation'] = self._call_model(observation_prompt)
        else:
            result['observation'] = observation

        if not condition:
            condition_prompt = f"""
Based on the following research background, please generate research conditions and environmental settings:

{context}

Requirements:
1. Conditions should describe the research environment and context
2. Conditions should include key assumptions
3. Conditions should be achievable in simulation
4. Express in clear and specific language

Please provide the condition description directly:
"""
            result['condition'] = self._call_model(condition_prompt)
        else:
            result['condition'] = condition

        logger.info(f"✓ Auto agent paradigm parameters generated")
        return result

    def _call_model(self, prompt: str) -> str:
        """Call the language model to generate content."""
        try:
            response = self.model(self.model.format(
                SystemMessage(content="You are a helpful research assistant. Generate concise, specific content based on the user's request."),
                UserMessage(content=prompt)
            ))
            return response.text.strip()
        except Exception as e:
            logger.warning(f"Model call failed: {e}")
            return "Auto-generation failed, please provide the parameter manually"