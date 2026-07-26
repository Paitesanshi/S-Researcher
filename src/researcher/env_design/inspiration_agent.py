"""
Inspiration Agent for generating research questions and simulation scenarios.

This unified module supports all research paradigms through configuration-driven prompts.
"""

import json
from typing import Dict, Any

from .agent_base import AgentBase
from .paradigm_config import get_paradigm_config, validate_input


class InspirationAgent(AgentBase):
    """
    Unified inspiration agent supporting all research paradigms.

    Generates research questions and simulation scenarios based on paradigm configuration.
    Each paradigm defines its required inputs and prompt templates.
    """

    def __init__(self, model_config=None, paradigm_key: str = "paradigm_1"):
        """
        Initialize the inspiration agent with specific paradigm configuration.

        Args:
            model_config (str, optional): The model configuration name to use.
            paradigm_key (str): The research paradigm to use (e.g., 'paradigm_1').
        """
        super().__init__("Inspiration Agent", model_config)
        self.paradigm_key = paradigm_key
        self.config = get_paradigm_config(paradigm_key)

    def _construct_system_prompt(self) -> str:
        """
        Constructs the system prompt based on paradigm configuration.

        Returns:
            str: The system prompt instructing the agent on its task.
        """
        return self.config["prompts"]["inspiration_system"]

    def _construct_user_prompt(self, input_data: Dict[str, Any]) -> str:
        """
        Constructs the user prompt from input data and paradigm template.

        Args:
            input_data: Dictionary containing paradigm-specific input fields.

        Returns:
            str: The formatted user prompt.
        """
        template = self.config["prompts"]["inspiration_user_template"]
        # Extract only the fields required by this paradigm
        prompt_vars = {
            field: input_data.get(field)
            for field in self.config["input_fields"]
        }
        return template.format(**prompt_vars)

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes the input data and generates research questions and scenarios.

        Args:
            input_data: Input data containing paradigm-specific fields.

        Returns:
            Dict containing generated scenarios and input metadata.

        Raises:
            ValueError: If required input fields are missing.
        """
        # Validate input data has all required fields
        validate_input(self.paradigm_key, input_data)

        # Construct prompts
        system_prompt = self._construct_system_prompt()
        user_prompt = self._construct_user_prompt(input_data)

        print("=" * 20)
        print("System Prompt:")
        print(system_prompt)
        print("=" * 20)
        print("User Prompt:")
        print(user_prompt)
        print("=" * 20)

        # Generate response
        response = self.generate_response(system_prompt, user_prompt)

        print("Response from Agent:")
        print(response)
        print("=" * 20)
        if "```json" in response:
            json_content = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            json_content = response.split("```")[1].strip()
        else:
            json_content = response

        # Parse JSON response
        try:
            parsed_response = json.loads(response)
            output_key = self.config["output_key"]
            return {
                output_key: parsed_response.get(output_key, parsed_response),
                "input_data": {
                    field: input_data.get(field)
                    for field in self.config["input_fields"]
                }
            }
        except json.JSONDecodeError:
            # Fallback for JSON wrapped in markdown code blocks
            try:

                parsed_response = json.loads(json_content)
                output_key = self.config["output_key"]
                return {
                    output_key: parsed_response.get(output_key, parsed_response),
                    "input_data": {
                        field: input_data.get(field)
                        for field in self.config["input_fields"]
                    }
                }
            except (json.JSONDecodeError, IndexError) as e:
                raise ValueError(
                    f"Failed to parse agent response as JSON. "
                    f"Response: {response[:200]}..."
                ) from e
