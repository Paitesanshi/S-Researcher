"""
Intelligent Paradigm Selector for automatic research paradigm selection.

Uses LLM to analyze user inputs and recommend the most suitable research paradigm.
"""

from typing import Optional
from loguru import logger
from onesim.models import get_model, SystemMessage, UserMessage


class ParadigmSelector:
    """
    LLM-based paradigm selector that analyzes research context and recommends
    the most appropriate paradigm.
    """

    SYSTEM_PROMPT = """You are an expert in social science research methodology. Your task is to analyze a research scenario and recommend the most suitable research paradigm.

Based on the unified S(M,C) ↦ O framework, we have 3 paradigms:

1. **deductive (M+C → O*)**: Use when you have a theory/mechanism and conditions, and want to predict outcomes
   - Input: theory (M) + condition (C)
   - Goal: Generate expected observations from theoretical predictions
   - Keywords: "验证", "基于...理论", "检验假设", "预测", "如果...会怎样"
   - Example: "Given social identity theory and in-group bias conditions, what behavioral patterns emerge?"

2. **inductive (O_real+C → M*)**: Use when you have real observations and want to discover underlying mechanisms
   - Input: observation (O_real) + condition (C)
   - Goal: Infer agent behavior mechanisms that explain the observations
   - Keywords: "观察到", "发现", "真实数据", "为什么出现", "背后的机制", "数据显示"
   - Example: "We observed that 90% of tweets spread to <10 people, but 1% go viral. What mechanisms explain this?"

3. **abductive (M+{C_i} → R*)**: Use when you want to quantify causal relationships by manipulating variables
   - Input: theory (M) + observation + condition variations ({C_i})
   - Goal: Quantify the causal effect of conditions on observations
   - Keywords: "影响", "效应", "干预", "因果关系", "量化", "不同水平"
   - Example: "Quantify how community participation rate (0%-100%) affects voter turnout"

Paradigm selection priority:
1. First check for inductive signals (most specific) - real observations, mechanisms to discover
2. Then check for abductive signals - causal quantification, intervention effects
3. Default to deductive - theory validation and prediction

Analyze the provided research context and respond with ONLY the paradigm name and a brief reason.

Format:
paradigm: <paradigm_name>
reason: <one sentence explanation>"""

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the paradigm selector.

        Args:
            model_name: Model configuration name to use for selection.
        """
        self.model_name = model_name
        self.model = get_model(config_name=model_name)

    def select_paradigm(
        self,
        scenario_description: Optional[str] = None,
        research_question: Optional[str] = None,
        research_topic: Optional[str] = None,
        theory: Optional[str] = None,
        observation: Optional[str] = None,
        condition: Optional[str] = None
    ) -> str:
        """
        Automatically select the most appropriate paradigm based on inputs.

        Args:
            scenario_description: Description of the research scenario
            research_question: Research question
            research_topic: Research topic (for backward compatibility)
            theory: Social science theory
            observation: Observed phenomenon
            condition: Conditions/constraints

        Returns:
            Paradigm name (e.g., 'deductive', 'inductive', 'abductive')
        """
        # Build context for LLM
        context_parts = []

        if scenario_description:
            context_parts.append(f"Scenario: {scenario_description}")
        if research_question:
            context_parts.append(f"Research Question: {research_question}")
        if research_topic:
            context_parts.append(f"Research Topic: {research_topic}")
        if theory:
            context_parts.append(f"Theory: {theory}")
        if observation:
            context_parts.append(f"Observation: {observation}")
        if condition:
            context_parts.append(f"Condition: {condition}")

        if not context_parts:
            logger.warning("No context provided for paradigm selection, defaulting to deductive")
            return "deductive"

        user_prompt = "\n".join(context_parts)

        logger.info("Analyzing research context for paradigm selection...")
        logger.debug(f"Context:\n{user_prompt}")

        try:
            # Generate selection using model
            response = self.model(self.model.format(
                SystemMessage(content=self.SYSTEM_PROMPT),
                UserMessage(content=user_prompt)
            ))

            # Parse response
            response_text = response.text.strip()
            logger.debug(f"LLM response: {response_text}")

            # Extract paradigm name from response
            paradigm_name = self._parse_paradigm_response(response_text)

            # Validate paradigm name (support both new and legacy names)
            valid_paradigms = [
                # New paradigms
                "deductive", "inductive", "abductive",
                # Legacy paradigms (backward compatibility)
                "theory_validation", "mechanism_discovery",
                "attribution_analysis", "boundary_exploration"
            ]

            if paradigm_name not in valid_paradigms:
                logger.warning(f"LLM returned unknown paradigm '{paradigm_name}', defaulting to deductive")
                return "deductive"

            # Migrate legacy paradigm names to new names
            from researcher.report_generation.core.config import migrate_paradigm
            migrated_name = migrate_paradigm(paradigm_name)

            if migrated_name != paradigm_name:
                logger.info(f"  Migrated '{paradigm_name}' → '{migrated_name}'")

            logger.info(f"✓ Selected paradigm: {migrated_name}")

            # Log reason if available
            if "reason:" in response_text.lower():
                reason_line = [line for line in response_text.split('\n') if 'reason:' in line.lower()]
                if reason_line:
                    logger.info(f"  Reason: {reason_line[0].split(':', 1)[1].strip()}")

            return migrated_name

        except Exception as e:
            logger.error(f"Failed to auto-select paradigm: {e}")
            logger.warning("Falling back to deductive paradigm")
            return "deductive"

    def _parse_paradigm_response(self, response: str) -> str:
        """
        Parse paradigm name from LLM response.

        Args:
            response: LLM response text

        Returns:
            Paradigm name (e.g., 'deductive', 'inductive', 'abductive')
        """
        # Try to extract from "paradigm: <name>" format
        for line in response.split('\n'):
            if 'paradigm:' in line.lower():
                paradigm_name = line.split(':', 1)[1].strip()
                return paradigm_name

        # Fallback: look for paradigm names in text (new paradigms first, then legacy)
        response_lower = response.lower()

        # Check new paradigms first (preferred)
        for name in ["deductive", "inductive", "abductive"]:
            if name in response_lower:
                return name

        # Check legacy paradigms (backward compatibility)
        for name in ["theory_validation", "mechanism_discovery",
                    "attribution_analysis", "boundary_exploration"]:
            if name.replace('_', ' ') in response_lower or name in response_lower:
                return name

        # Default to deductive
        return "deductive"
