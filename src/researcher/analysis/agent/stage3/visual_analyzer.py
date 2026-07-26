import json
import argparse
from typing import Dict, Any, Optional, List
from pathlib import Path
import os
from researcher.analysis.common import get_model_config_path

try:
    from src.onesim.models.core.model_manager import ModelManager
    from src.onesim.models.core.message import Message
    from src.researcher.analysis.agent.stage3.data_loader import DataLoader
except ImportError:
    import sys
    sys.path.append(str(Path.cwd()))
    from src.onesim.models.core.model_manager import ModelManager
    from src.onesim.models.core.message import Message
    from src.researcher.analysis.agent.stage3.data_loader import DataLoader

class VisualAnalyzer:
    def __init__(self, config_name: Optional[str] = None):
        self.model = None
        try:
            env_name = os.environ.get("ANALYSIS_COMMON_MODEL_NAME") or os.environ.get("ONESIM_MODEL_NAME") or "default-chat"
            if env_name == "openai-gpt4o":
                env_name = "gpt-4o"
            config_name = config_name or env_name
            config_path = get_model_config_path()
            self.model_manager = ModelManager.get_instance()
            self.model_manager.initialize(str(config_path))
            self.model = self.model_manager.get_model(config_name=config_name)
        except Exception as e:
            print(f"Warning: Failed to initialize VisualAnalyzer model: {e}")

    def _manual_format(self, message) -> List[Dict]:
        """
        Manually format the message to a list of dicts expected by the OpenAI API.
        This bypasses potential isinstance() failures due to import path mismatches.
        """
        content_parts = []
        
        # Text
        if message.content:
            content_parts.append({"type": "text", "text": str(message.content)})
            
        # Images
        if hasattr(message, "images") and message.images:
            import base64
            for img_path in message.images:
                path_obj = Path(img_path)
                if path_obj.exists():
                    try:
                        with open(path_obj, "rb") as f:
                            b64 = base64.b64encode(f.read()).decode("utf-8")
                        ext = path_obj.suffix.lower().replace(".", "")
                        if ext == "jpg": ext = "jpeg"
                        # Handle potential empty ext
                        if not ext: ext = "jpeg"
                        
                        content_parts.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/{ext};base64,{b64}"}
                        })
                    except Exception as e:
                        print(f"Error encoding image {img_path}: {e}")
        
        return [{
            "role": getattr(message, "role", "user"),
            "content": content_parts
        }]

    def analyze(self, figure_path: Optional[str], research_question: str, stats_summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform visual analysis using a multimodal model.
        """
        if not figure_path:
            return {"status": "skipped", "reason": "No figure path provided"}
        
        if self.model is None:
            return {"status": "error", "reason": "Model not initialized"}

        path_obj = Path(figure_path)
        if not path_obj.exists():
             return {"status": "skipped", "reason": f"Figure file not found: {figure_path}"}

        # Construct Prompt
        stats_text = "No statistical summary provided."
        if stats_summary:
            stats_text = json.dumps(stats_summary, indent=2)

        prompt = (
            f"You are an expert researcher. Analyze the provided figure in the context of the research question.\n\n"
            f"Research Question: {research_question}\n\n"
            f"Statistical Context:\n{stats_text}\n\n"
            f"Please describe the key trends or patterns visible in the image. "
            f"Do they support the statistical findings? Provide a concise interpretation."
        )

        message = Message(
            role="user",
            content=prompt,
            images=[str(path_obj)]
        )

        try:
            # Use manual formatting to be safe against import/class mismatch issues
            formatted_messages = self._manual_format(message)
            response = self.model(formatted_messages)
            return {
                "status": "success",
                "analysis": response.text,
                "model_used": getattr(self.model, "model_name", "unknown")
            }
        except Exception as e:
            return {"status": "error", "reason": str(e)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Visual Analyzer")
    parser.add_argument("--project-name", required=True, help="Project name")
    parser.add_argument("--item-id", required=True, help="Item ID")
    
    args = parser.parse_args()
    
    # Load Context
    loader = DataLoader(args.project_name)
    context = loader.get_analysis_context(args.item_id)
    
    fig_path = context.get("figure_path")
    print(f"Figure Path: {fig_path}")
    
    analyzer = VisualAnalyzer()
    result = analyzer.analyze(fig_path, context["item"]["research_question"], stats_summary={"note": "Test run"})
    
    print("\nVisual Analysis Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
