import json
import os
import re
from typing import Any, Dict, List, Optional, Union

try:
    from ..llm.agent_client import SimpleChatLLM
except Exception:
    try:
        from researcher.analysis.agent.llm.agent_client import SimpleChatLLM
    except Exception:
        # Fallback for direct execution
        try:
            from src.researcher.analysis.agent.llm.agent_client import SimpleChatLLM
        except Exception:
            # Last resort
            try:
                from src.researcher.analysis.agent.agent_client import SimpleChatLLM # type: ignore
            except Exception:
                SimpleChatLLM = None

from src.researcher.analysis.agent.planning.data_profile import DataMetric

class AnalysisPlannerAgent:
    """
    Agent responsible for generating a rigorous research analysis plan 
    by bridging theoretical hypotheses (or research questions) with available empirical data.
    """
    
    def __init__(
        self,
        model_config_name: Optional[str] = None,
        model_config_path: Optional[str] = None,
    ) -> None:
        self.model_config_name = (
            model_config_name
            or os.environ.get("ONESIM_MODEL_NAME")
            or "default-chat"
        )
        self.model_config_path = (
            model_config_path
            or os.environ.get("ONESIM_MODEL_CONFIG", "config/model_config.json")
        )
        try:
            self.llm = SimpleChatLLM(
                config_name=self.model_config_name, config_path=self.model_config_path
            )
        except Exception as e:
            # If LLM init fails, we might need a dummy or raise error
            print(f"Warning: Failed to init LLM: {e}")
            self.llm = None

    def _clean_json_string(self, text: str) -> str:
        """
        Robustly extract JSON object from LLM response.
        Handles markdown code blocks, prefixes, and suffixes.
        """
        text = text.strip()
        
        # 1. Try to find content within ```json ... ``` or ``` ... ```
        pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1)
            
        # 2. Try to find the first '{' and last '}'
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            return text[start_idx : end_idx + 1]
            
        return text

    def plan_analysis(
        self, 
        project_name: str, 
        summary_context: Dict[str, Any], 
        data_profile: List[DataMetric]
    ) -> Dict[str, Any]:
        """
        Generates the analysis plan JSON.
        
        Args:
            project_name: Name of the project.
            summary_context: A dictionary containing:
                - hypotheses: List[str] (Optional)
                - core_question: str (Optional)
                - independent_variable: Any (Optional)
                - dependent_variable: Any (Optional)
                - scenario_description: str (Optional)
            data_profile: List of available DataMetrics.
        """
        if not self.llm:
            return {"error": "LLM not initialized"}

        # Serialize data profile for the prompt
        metrics_desc = [m.to_dict() for m in data_profile]
        
        hypotheses = summary_context.get("hypotheses", [])
        core_question = summary_context.get("core_question", "")
        
        system_prompt = (
            "You are a Senior Research Scientist in Social Simulation. "
            "Your goal is to design a rigorous analysis plan based on the 'S: (M, C) -> O' framework. "
            "You must adapt your strategy based on the available information:\n"
            "1. Deductive (Verification): If specific hypotheses are provided, design analysis to test them.\n"
            "2. Inductive/Exploratory: If hypotheses are missing, use the Core Question, Scenario Config (C), and Outcome Data (O) "
            "to formulate research questions and analysis tasks that reveal system behaviors.\n\n"
            "CRITICAL: Output strictly valid JSON only. Do not include any thinking process or markdown text outside the JSON object."
        )
        
        instruction = (
            "Generate a JSON object with a key 'analysis_items'. "
            "Each item must map a research question (or hypothesis) to a specific analysis task. "
            "If hypotheses are missing, you MUST formulate 3-5 key research questions based on the available metrics "
            "and the core research goal. Focus on how independent variables (C) might affect the metrics (O)."
        )

        user_query = json.dumps({
            "project_name": project_name,
            "research_context": summary_context,
            "available_metrics (O)": metrics_desc,
            "instruction": instruction,
            "schema_requirements": {
                "analysis_items": [
                    {
                        "id": "unique_id_string",
                        "research_question": "Specific question to answer (generated or from input)",
                        "hypothesis_ref": "The hypothesis text being tested, or 'Exploratory' if generated",
                        "analysis_type": "One of: ['group_comparison', 'trend_analysis', 'correlation', 'intervention_effect', 'descriptive']",
                        "visualization_needed": "boolean (true if this analysis requires a chart, false if purely text/statistical)",
                        "feasibility": {
                            "data_available": "boolean (true if a matching metric exists)",
                            "data_granularity_sufficient": "boolean",
                            "sample_size_estimate": "One of: ['unknown', 'small', 'medium', 'large']"
                        },
                        "evidence_support": {
                            "file_name": "Exact filename from available_metrics",
                            "metric_category": "Category from available_metrics",
                            "data_type": "Data type from available_metrics",
                            "reasoning": "Why this metric fits the inquiry"
                        },
                        "visualization_hint": {
                            "suggested_plot_type": "e.g., 'bar', 'line', 'scatter', 'box'",
                            "x_axis": "Field to use for X",
                            "y_axis": "Field to use for Y",
                            "comparison_aspect": "What is being compared?"
                        }
                    }
                ]
            },
            "constraints": [
                "Only set 'data_available': true if you find a metric with matching category/description.",
                "If data is missing, set 'data_available': false and 'analysis_type': 'descriptive' (or skip it).",
                "Set 'visualization_needed': false for abstract analysis or when data is insufficient.",
                "Ensure 'evidence_support.file_name' matches exactly one of the provided files."
            ]
        }, ensure_ascii=False)

        try:
            response = self.llm.chat(user_query, system_prompt=system_prompt)
            
            # Robust cleaning
            cleaned_response = self._clean_json_string(response)
            
            plan = json.loads(cleaned_response)
            return plan
        except Exception as e:
            return {
                "error": str(e),
                "raw_response": locals().get("response", "")
            }

if __name__ == "__main__":
    # CLI Test
    import sys
    from src.researcher.analysis.agent.planning.data_profile import DataType, Granularity
    
    # Mock data for testing
    mock_metrics = [
        DataMetric(
            category="Follower Contribution", 
            file_name="contributions.json", 
            file_path="/tmp/contributions.json",
            description="Daily contributions",
            data_type=DataType.TIMESERIES,
            granularity=Granularity.GROUP,
            sample_size=100
        )
    ]
    
    agent = AnalysisPlannerAgent()
    if agent.llm:
        print("LLM initialized. Running test plan...")
        # Test Inductive Mode (No hypotheses)
        context = {
            "core_question": "How does follower behavior evolve?",
            "hypotheses": [],
            "scenario_description": "A simulation of public goods game."
        }
        result = agent.plan_analysis(
            project_name="test_project",
            summary_context=context,
            data_profile=mock_metrics
        )
        print(json.dumps(result, indent=2))
    else:
        print("Skipping LLM test (no client available).")
