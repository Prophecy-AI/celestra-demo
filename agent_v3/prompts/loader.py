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

    def load_prompt(self, prompt_name: str, variables: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Load a tool prompt YAML file and render it with variables

        Args:
            prompt_name: Name of prompt file without extension (e.g., 'text_to_sql_rx')
            variables: Dict of variables to inject into the template

        Returns:
            Rendered prompt string, or None if no system_prompt field exists

        Raises:
            FileNotFoundError: If prompt file doesn't exist
            ValueError: If YAML is invalid
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

        # Return None if no system_prompt (e.g., for non-LLM tools)
        if 'system_prompt' not in prompt_data:
            return None

        prompt_template = prompt_data['system_prompt']

        # Render with Jinja2 if variables provided
        if variables:
            template = Template(prompt_template)
            rendered = template.render(**variables)
            return rendered

        return prompt_template

    def load_system_prompt(self, variables: Optional[Dict[str, Any]] = None) -> str:
        """
        Load the main orchestrator system prompt with dynamic tools list

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

        # Build dynamic tools list from all tool YAMLs
        tools_list = self._build_tools_list()
        variables['tools_list'] = tools_list

        # Render with Jinja2
        template = Template(prompt_template)
        rendered = template.render(**variables)
        return rendered

    def _build_tools_list(self) -> str:
        """
        Build tools list from tool YAMLs specified in main_orchestrator.yaml

        Returns:
            Concatenated string of all tool descriptions for orchestrator
        """
        # Load main orchestrator to get tools list
        prompt_path = self.system_dir / "main_orchestrator.yaml"

        if not prompt_path.exists():
            return ""

        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                orchestrator_data = yaml.safe_load(f)
        except Exception:
            return ""

        if not isinstance(orchestrator_data, dict) or 'tools' not in orchestrator_data:
            return ""

        tool_names = orchestrator_data['tools']
        if not isinstance(tool_names, list):
            return ""

        tool_infos = []

        # Load each specified tool YAML and extract orchestrator_info
        for tool_name in tool_names:
            tool_path = self.tools_dir / f"{tool_name}.yaml"

            if not tool_path.exists():
                continue

            try:
                with open(tool_path, 'r', encoding='utf-8') as f:
                    tool_data = yaml.safe_load(f)

                # Extract orchestrator_info if it exists
                if isinstance(tool_data, dict) and 'orchestrator_info' in tool_data:
                    orchestrator_info = tool_data['orchestrator_info']
                    if orchestrator_info and isinstance(orchestrator_info, str):
                        tool_infos.append(orchestrator_info.strip())

            except Exception:
                # Skip invalid YAML files silently
                continue

        # Concatenate with newlines
        return '\n'.join(tool_infos)

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
