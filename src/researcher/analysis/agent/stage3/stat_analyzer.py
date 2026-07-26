import json
import argparse
from typing import Dict, Any, Optional, List, Union
import pandas as pd
from pathlib import Path
import os
from researcher.analysis.common import get_model_config_path

try:
    from src.researcher.analysis.agent.llm.enhanced_llm_adapter import EnhancedStatAgentLLMAdapter
    from src.researcher.analysis.agent.stage3.data_loader import DataLoader
except ImportError:
    # Fallback for direct execution if PYTHONPATH issues
    import sys
    sys.path.append(str(Path.cwd()))
    from src.researcher.analysis.agent.llm.enhanced_llm_adapter import EnhancedStatAgentLLMAdapter
    from src.researcher.analysis.agent.stage3.data_loader import DataLoader

class StatAnalyzer:
    def __init__(self, config_name: Optional[str] = None):
        env_name = os.environ.get("ANALYSIS_COMMON_MODEL_NAME") or os.environ.get("ONESIM_MODEL_NAME") or "default-chat"
        if env_name == "openai-gpt4o":
            env_name = "gpt-4o"
        config_name = config_name or env_name
        config_path = get_model_config_path()
        try:
            self.adapter = EnhancedStatAgentLLMAdapter(config_name=config_name, config_path=str(config_path))
        except Exception as e:
            print(f"Warning: Failed to initialize EnhancedStatAgentLLMAdapter: {e}")
            self.adapter = None

    def analyze(self, data: Union[List[Dict], pd.DataFrame], research_question: str, analysis_type: str) -> Dict[str, Any]:
        """
        Perform statistical analysis on the data guided by the research question.
        """
        if self.adapter is None:
            return {
                "error": "Statistical Analyzer not initialized (likely due to missing dependencies or config)",
                "structured_analysis": None
            }
            
        # Context to guide the LLM
        context = {
            "research_question": research_question,
            "analysis_type": analysis_type,
            "data_overview": {
                "description": f"Data for research question: {research_question}",
                "analysis_goal": f"Perform {analysis_type} analysis"
            }
        }

        # Use the adapter to analyze data
        # The adapter will plan tool calls and execute them
        result = self.adapter.analyze_data(data, context=context)
        
        # Result contains 'analysis' (text/json string) and 'metadata'
        # We try to parse the analysis string if it is JSON
        parsed_analysis = result.get("analysis")
        if isinstance(parsed_analysis, str):
            try:
                # Strip markdown code blocks if present
                clean_analysis = parsed_analysis.strip()
                if clean_analysis.startswith("```json"):
                    clean_analysis = clean_analysis[7:]
                if clean_analysis.startswith("```"):
                    clean_analysis = clean_analysis[3:]
                if clean_analysis.endswith("```"):
                    clean_analysis = clean_analysis[:-3]
                
                clean_analysis = clean_analysis.strip()
                
                # Attempt to parse if it looks like JSON
                if clean_analysis.startswith("{"):
                    parsed_analysis = json.loads(clean_analysis)
            except:
                pass # Keep as string if parsing fails
        
        return {
            "raw_result": result,
            "structured_analysis": parsed_analysis
        }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Stat Analyzer")
    parser.add_argument("--project-name", required=True, help="Project name")
    parser.add_argument("--item-id", required=True, help="Item ID to analyze")
    
    args = parser.parse_args()
    
    # Load Data
    loader = DataLoader(args.project_name)
    context = loader.get_analysis_context(args.item_id)
    
    if context.get("data") is None:
        print(f"Error: No data found for item {args.item_id}")
        exit(1)
        
    item = context["item"]
    data = context["data"]
    
    # Initialize Analyzer
    analyzer = StatAnalyzer()
    
    print(f"Analyzing Item: {item['id']}")
    print(f"Question: {item['research_question']}")
    print(f"Type: {item['analysis_type']}")
    
    analysis_result = analyzer.analyze(data, item['research_question'], item['analysis_type'])
    
    print("\nAnalysis Result:")
    print(json.dumps(analysis_result.get("structured_analysis", "Error parsing analysis"), indent=2, ensure_ascii=False))
