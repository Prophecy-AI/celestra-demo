"""
Prompt loader for agent_v3 - loads and renders prompts from YAML files
"""
import os
import yaml
from typing import Dict, Any, Optional
from jinja2 import Template
from pathlib import Path


class PromptLoader:
    """Load and render prompts from YAML files"""

    def __init__(self):
        # Get the prompts directory path
        self.prompts_dir = Path(__file__).parent
        self.tools_dir = self.prompts_dir / "tools"
        self.system_dir = self.prompts_dir / "system"

    def load_prompt(self, prompt_name: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """
        Load a tool prompt YAML file and render it with variables

        Args:
            prompt_name: Name of prompt file without extension (e.g., 'text_to_sql_rx')
            variables: Dict of variables to inject into the template

        Returns:
            Rendered prompt string

        Raises:
            FileNotFoundError: If prompt file doesn't exist
            ValueError: If YAML is invalid or missing required fields
        """
        prompt_path = self.tools_dir / f"{prompt_name}.yaml"

        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        # Load YAML
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_data = yaml.safe_load(f)

        # Validate schema
        if not isinstance(prompt_data, dict):
            raise ValueError(f"Prompt file must contain a YAML dictionary: {prompt_path}")

        if 'system_prompt' not in prompt_data:
            raise ValueError(f"Prompt file missing 'system_prompt' field: {prompt_path}")

        prompt_template = prompt_data['system_prompt']

        # Render with Jinja2 if variables provided
        if variables:
            template = Template(prompt_template)
            rendered = template.render(**variables)
            return rendered

        return prompt_template

    def load_system_prompt(self, variables: Optional[Dict[str, Any]] = None) -> str:
        """
        Load the main orchestrator system prompt

        Args:
            variables: Dict of variables to inject (e.g., current_date, current_time)

        Returns:
            Rendered system prompt string
        """
        prompt_path = self.system_dir / "main_orchestrator.yaml"

        if not prompt_path.exists():
            raise FileNotFoundError(f"System prompt file not found: {prompt_path}")

        # Load YAML
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_data = yaml.safe_load(f)

        # Validate
        if not isinstance(prompt_data, dict):
            raise ValueError(f"System prompt must be a YAML dictionary: {prompt_path}")

        if 'system_prompt' not in prompt_data:
            raise ValueError(f"System prompt missing 'system_prompt' field: {prompt_path}")

        prompt_template = prompt_data['system_prompt']

        # Inject current date/time if not provided
        if variables is None:
            from datetime import datetime
            variables = {
                'current_date': datetime.now().strftime("%Y-%m-%d"),
                'current_time': datetime.now().strftime("%H:%M:%S")
            }

        # Render with Jinja2
        template = Template(prompt_template)
        rendered = template.render(**variables)
        return rendered

    def get_prompt_metadata(self, prompt_name: str) -> Dict[str, Any]:
        """
        Get metadata from a prompt file without rendering

        Args:
            prompt_name: Name of prompt file

        Returns:
            Dictionary with metadata (name, model, temperature, etc.)
        """
        prompt_path = self.tools_dir / f"{prompt_name}.yaml"

        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_data = yaml.safe_load(f)

        # Return everything except the prompt itself
        metadata = {k: v for k, v in prompt_data.items() if k != 'system_prompt'}
        return metadata

    def list_tool_prompts(self) -> list[str]:
        """List all available tool prompt names"""
        if not self.tools_dir.exists():
            return []

        prompts = []
        for path in self.tools_dir.glob("*.yaml"):
            prompts.append(path.stem)

        return sorted(prompts)

    def validate_prompt_file(self, prompt_path: Path) -> Optional[str]:
        """
        Validate a prompt YAML file

        Args:
            prompt_path: Path to prompt file

        Returns:
            Error message if invalid, None if valid
        """
        if not prompt_path.exists():
            return f"File does not exist: {prompt_path}"

        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            return f"Invalid YAML: {e}"

        if not isinstance(data, dict):
            return "Prompt file must contain a YAML dictionary"

        if 'system_prompt' not in data:
            return "Missing required field: 'system_prompt'"

        if not isinstance(data['system_prompt'], str):
            return "'system_prompt' must be a string"

        # Optional fields validation
        if 'name' in data and not isinstance(data['name'], str):
            return "'name' must be a string"

        if 'model' in data and not isinstance(data['model'], str):
            return "'model' must be a string"

        if 'temperature' in data and not isinstance(data['temperature'], (int, float)):
            return "'temperature' must be a number"

        if 'max_tokens' in data and not isinstance(data['max_tokens'], int):
            return "'max_tokens' must be an integer"

        if 'variables' in data and not isinstance(data['variables'], list):
            return "'variables' must be a list"

        return None
