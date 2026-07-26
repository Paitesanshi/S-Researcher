"""
Report Configuration System
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
from pathlib import Path
from loguru import logger


class ResearchParadigm(Enum):
    """
    Unified research paradigm types based on S(M,C) ↦ O framework.

    All research paradigms share the same simulation process:
    S(M, C) ↦ O
    where:
    - S: Social Simulator (Agent-based simulation system)
    - M: Mechanism (Agent behavior rules, theories, interaction protocols)
    - C: Configuration (Scenario parameters, conditions, intervention variables)
    - O: Outcome (Emergent phenomena, observed data, system states)

    The difference lies in what is "known" and what is "solved for":
    1. Deductive: M+C → O* (predict outcomes from theory)
    2. Inductive: O_real+C → M* (infer mechanisms from observations)
    3. Abductive: M+{C_i} → R* (quantify causal relationships)
    """
    # New unified paradigms (3 types)
    DEDUCTIVE = "deductive"    # 演绎型: M+C → O*
    INDUCTIVE = "inductive"    # 归纳型: O_real+C → M*
    ABDUCTIVE = "abductive"    # 溯因型: M+{C_i} → R*

    # Legacy paradigms (backward compatibility - will be auto-migrated)
    THEORY_VALIDATION = "theory_validation"      # T+C → O → maps to DEDUCTIVE
    MECHANISM_DISCOVERY = "mechanism_discovery"  # O+C → T → maps to INDUCTIVE
    BOUNDARY_EXPLORATION = "boundary_exploration"# T+O → C_boundary → maps to ABDUCTIVE
    ATTRIBUTION_ANALYSIS = "attribution_analysis"# T+O → C_weight → maps to ABDUCTIVE


# Backward compatibility mapping
LEGACY_PARADIGM_MAPPING = {
    "theory_validation": "deductive",
    "mechanism_discovery": "inductive",
    "attribution_analysis": "abductive",
    "boundary_exploration": "abductive"
}


def migrate_paradigm(paradigm_value: str) -> str:
    """
    Migrate legacy paradigm names to new unified paradigm names.

    Args:
        paradigm_value: Paradigm value string (e.g., 'theory_validation', 'deductive')

    Returns:
        New paradigm value (e.g., 'deductive', 'inductive', 'abductive')
    """
    # If already new paradigm, return as-is
    if paradigm_value in ["deductive", "inductive", "abductive"]:
        return paradigm_value

    # Check legacy mapping
    if paradigm_value in LEGACY_PARADIGM_MAPPING:
        logger.warning(
            f"Legacy paradigm '{paradigm_value}' detected, "
            f"auto-migrating to '{LEGACY_PARADIGM_MAPPING[paradigm_value]}'"
        )
        return LEGACY_PARADIGM_MAPPING[paradigm_value]

    # Unknown paradigm - default to deductive
    logger.error(f"Unknown paradigm '{paradigm_value}', defaulting to 'deductive'")
    return "deductive"


@dataclass
class ParadigmConfig:
    """Configuration parameters for specific research paradigms"""
    methodology_focus: str
    analysis_approach: str
    result_presentation: str
    writing_style: str
    evaluation_criteria: List[str]


@dataclass
class ReportConfig:
    """Configuration for report generation"""

    title: str = "Research Report"
    author: str = "AI Social Researcher"
    language: str = "en"

    include_abstract: bool = True
    include_literature_review: bool = True
    include_bibliography: bool = True
    max_literature_papers: int = 20

    output_format: str = "latex"
    enable_review: bool = True
    max_review_iterations: int = 2

    # LaTeX compilation options
    compile_pdf: bool = True
    latex_engine: str = "xelatex"
    clean_aux_files: bool = True

    model_config_name: Optional[str] = None

    reference_paper_path: Optional[str] = None
    outline_template_path: Optional[str] = None

    custom_sections: List[str] = field(default_factory=list)
    section_weights: Dict[str, float] = field(default_factory=dict)
    quality_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "technical_rigor": 3.0,
        "clarity": 3.5,
        "novelty": 3.0,
        "validation": 3.0,
        "writing_quality": 3.5
    })

    _paradigm: Optional[ResearchParadigm] = field(default=None, init=False)

    @property
    def research_paradigm(self) -> Optional[ResearchParadigm]:
        """Get inferred research paradigm"""
        return self._paradigm

    def set_paradigm(self, paradigm: ResearchParadigm):
        """Set inferred research paradigm"""
        self._paradigm = paradigm

    def get_paradigm_config(self) -> Optional[ParadigmConfig]:
        """Get paradigm-specific configuration"""
        if not self._paradigm:
            return None

        # Migrate legacy paradigm if needed
        paradigm_value = self._paradigm.value if isinstance(self._paradigm, ResearchParadigm) else str(self._paradigm)
        migrated_value = migrate_paradigm(paradigm_value)

        # Unified paradigm configurations (3 types)
        paradigm_configs = {
            "deductive": ParadigmConfig(
                methodology_focus="hypothesis_testing",
                analysis_approach="deductive",
                result_presentation="validation_metrics",
                writing_style="formal_theoretical",
                evaluation_criteria=["theoretical_rigor", "hypothesis_clarity", "statistical_validation"]
            ),
            "inductive": ParadigmConfig(
                methodology_focus="mechanism_discovery",
                analysis_approach="inductive",
                result_presentation="emergent_mechanisms",
                writing_style="exploratory_analytical",
                evaluation_criteria=["hypothesis_quality", "mechanism_validation", "generalizability"]
            ),
            "abductive": ParadigmConfig(
                methodology_focus="causal_quantification",
                analysis_approach="experimental",
                result_presentation="causal_relationships",
                writing_style="quantitative_analytical",
                evaluation_criteria=["causal_clarity", "effect_quantification", "robustness"]
            ),
            # Legacy mappings (backward compatibility)
            "theory_validation": ParadigmConfig(
                methodology_focus="hypothesis_testing",
                analysis_approach="deductive",
                result_presentation="validation_metrics",
                writing_style="formal_theoretical",
                evaluation_criteria=["theoretical_rigor", "hypothesis_clarity", "statistical_validation"]
            ),
            "mechanism_discovery": ParadigmConfig(
                methodology_focus="pattern_identification",
                analysis_approach="inductive",
                result_presentation="emergent_patterns",
                writing_style="exploratory_analytical",
                evaluation_criteria=["pattern_discovery", "inductive_reasoning", "generalizability"]
            ),
            "boundary_exploration": ParadigmConfig(
                methodology_focus="parameter_analysis",
                analysis_approach="parametric",
                result_presentation="threshold_identification",
                writing_style="systematic_comparative",
                evaluation_criteria=["parameter_coverage", "threshold_identification", "robustness"]
            ),
            "attribution_analysis": ParadigmConfig(
                methodology_focus="factor_isolation",
                analysis_approach="analytical",
                result_presentation="contribution_quantification",
                writing_style="quantitative_analytical",
                evaluation_criteria=["factor_isolation", "contribution_quantification", "sensitivity"]
            )
        }
        return paradigm_configs.get(migrated_value) or paradigm_configs["deductive"]

    def get_writing_style(self) -> str:
        """Determine writing style based on available references"""
        if self.reference_paper_path and Path(self.reference_paper_path).exists():
            return "reference_based"
        elif self.outline_template_path and Path(self.outline_template_path).exists():
            return "template_based"
        else:
            return "standard_academic"

    def get_section_modifier(self, section_name: str) -> str:
        """Get section-specific prompt modifier"""
        if not self._paradigm:
            return ""

        # Migrate legacy paradigm if needed
        paradigm_value = self._paradigm.value if isinstance(self._paradigm, ResearchParadigm) else str(self._paradigm)
        migrated_value = migrate_paradigm(paradigm_value)

        # Unified modifiers (3 paradigms)
        modifiers = {
            "deductive": {
                "methodology": "Focus on hypothesis formulation and testing procedures from theory.",
                "results": "Emphasize statistical validation and theoretical confirmation.",
                "discussion": "Discuss theoretical implications and validation success."
            },
            "inductive": {
                "methodology": "Emphasize multi-hypothesis generation and validation approach. Describe the process of generating candidate mechanisms, implementing them as agent decision logic, and evaluating fit with real observations.",
                "results": "Highlight discovered mechanisms, hypothesis comparison, and best-fit mechanism selection with quantitative fitness metrics.",
                "discussion": "Analyze mechanism validity, theoretical insights, and generalizability of discovered patterns."
            },
            "abductive": {
                "methodology": "Detail experimental design with controlled variable manipulation. Describe independent variable levels, control variables, and replication strategy.",
                "results": "Present causal relationship quantification with effect sizes, statistical significance, and dose-response curves.",
                "discussion": "Interpret causal mechanisms, practical implications, and policy recommendations based on quantified effects."
            },
            # Legacy mappings
            "theory_validation": {
                "methodology": "Focus on hypothesis formulation and testing procedures.",
                "results": "Emphasize statistical validation and theoretical confirmation.",
                "discussion": "Discuss theoretical implications and validation success."
            },
            "mechanism_discovery": {
                "methodology": "Emphasize exploratory analysis and pattern detection methods.",
                "results": "Highlight discovered patterns and emergent mechanisms.",
                "discussion": "Analyze mechanism validity and broader implications."
            },
            "boundary_exploration": {
                "methodology": "Detail parameter space exploration and sensitivity analysis.",
                "results": "Present threshold identification and boundary characterization.",
                "discussion": "Discuss boundary stability and practical implications."
            },
            "attribution_analysis": {
                "methodology": "Describe factor isolation and contribution analysis methods.",
                "results": "Quantify factor contributions and relative importance.",
                "discussion": "Interpret factor interactions and practical significance."
            }
        }

        return modifiers.get(migrated_value, {}).get(section_name.lower(), "")

    def validate(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []

        if not self.title.strip():
            issues.append("Title cannot be empty")

        if not self.author.strip():
            issues.append("Author cannot be empty")

        if self.max_literature_papers < 5:
            issues.append("Max literature papers should be at least 5")

        if self.max_review_iterations < 1:
            issues.append("Max review iterations should be at least 1")

        if self.reference_paper_path and not Path(self.reference_paper_path).exists():
            issues.append(f"Reference paper not found: {self.reference_paper_path}")

        if self.outline_template_path and not Path(self.outline_template_path).exists():
            issues.append(f"Outline template not found: {self.outline_template_path}")

        return issues
