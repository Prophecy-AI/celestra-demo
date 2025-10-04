"""
Tool generator for creating new tools from templates
"""
import os
from typing import Dict, Any, Tuple, List, Optional
from pathlib import Path
from .templates import ToolTemplate, SQLToolTemplate


class ToolGenerator:
    """Generate new tools from templates"""

    def __init__(self):
        self.templates: Dict[str, ToolTemplate] = {
            "sql": SQLToolTemplate(),
            # Future templates can be added here:
            # "api": APIToolTemplate(),
            # "computation": ComputationToolTemplate(),
        }

        # Get paths
        self.tools_dir = Path(__file__).parent
        self.prompts_dir = self.tools_dir.parent / "prompts" / "tools"

    def list_templates(self) -> List[str]:
        """List available template types"""
        return list(self.templates.keys())

    def get_template_schema(self, template_type: str) -> Optional[Dict[str, Any]]:
        """
        Get the configuration schema for a template type

        Args:
            template_type: Type of template (e.g., "sql")

        Returns:
            Schema dictionary or None if template not found
        """
        if template_type not in self.templates:
            return None

        return self.templates[template_type].get_config_schema()

    def validate_config(self, template_type: str, config: Dict[str, Any]) -> Optional[str]:
        """
        Validate a configuration for a template

        Args:
            template_type: Type of template
            config: Configuration dictionary

        Returns:
            Error message if invalid, None if valid
        """
        if template_type not in self.templates:
            return f"Unknown template type: {template_type}"

        template = self.templates[template_type]
        return template.validate_config(config)

    def create_tool(
        self,
        template_type: str,
        config: Dict[str, Any],
        dry_run: bool = False
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Create a new tool from a template

        Args:
            template_type: Type of template to use (e.g., "sql")
            config: Configuration dictionary with tool parameters
            dry_run: If True, return generated code without writing files

        Returns:
            Tuple of (python_file_path, prompt_file_path, error_message)
            If dry_run=True, returns (python_code, prompt_yaml, None)
            If error, returns (None, None, error_message)
        """
        # Validate template type
        if template_type not in self.templates:
            return None, None, f"Unknown template type: {template_type}. Available: {self.list_templates()}"

        template = self.templates[template_type]

        # Validate configuration
        error = template.validate_config(config)
        if error:
            return None, None, f"Invalid configuration: {error}"

        # Generate code and prompt
        try:
            tool_code = template.generate_tool_code(config)
            prompt_yaml = template.generate_prompt(config)
        except Exception as e:
            return None, None, f"Failed to generate tool: {str(e)}"

        # If dry run, return the generated content
        if dry_run:
            return tool_code, prompt_yaml, None

        # Write files
        tool_name = config["tool_name"]

        # Python file path (e.g., tools/text_to_sql_pharmacy.py)
        python_filename = f"{tool_name}.py"
        python_path = self.tools_dir / python_filename

        # Prompt file path (e.g., prompts/tools/text_to_sql_pharmacy.yaml)
        prompt_filename = f"{tool_name}.yaml"
        prompt_path = self.prompts_dir / prompt_filename

        # Check if files already exist
        if python_path.exists():
            return None, None, f"Tool file already exists: {python_path}"
        if prompt_path.exists():
            return None, None, f"Prompt file already exists: {prompt_path}"

        # Write Python tool file
        try:
            with open(python_path, 'w', encoding='utf-8') as f:
                f.write(tool_code)
        except Exception as e:
            return None, None, f"Failed to write Python file: {str(e)}"

        # Write YAML prompt file
        try:
            with open(prompt_path, 'w', encoding='utf-8') as f:
                f.write(prompt_yaml)
        except Exception as e:
            # Clean up Python file if prompt write fails
            if python_path.exists():
                python_path.unlink()
            return None, None, f"Failed to write prompt file: {str(e)}"

        return str(python_path), str(prompt_path), None

    def preview_tool(self, template_type: str, config: Dict[str, Any]) -> Tuple[str, str, Optional[str]]:
        """
        Preview generated code without creating files

        Args:
            template_type: Type of template
            config: Configuration dictionary

        Returns:
            Tuple of (python_code, prompt_yaml, error_message)
        """
        return self.create_tool(template_type, config, dry_run=True)

    def delete_tool(self, tool_name: str) -> Optional[str]:
        """
        Delete a tool and its prompt

        Args:
            tool_name: Name of the tool to delete

        Returns:
            Error message if failed, None if successful
        """
        python_path = self.tools_dir / f"{tool_name}.py"
        prompt_path = self.prompts_dir / f"{tool_name}.yaml"

        errors = []

        # Delete Python file
        if python_path.exists():
            try:
                python_path.unlink()
            except Exception as e:
                errors.append(f"Failed to delete {python_path}: {str(e)}")
        else:
            errors.append(f"Python file not found: {python_path}")

        # Delete prompt file
        if prompt_path.exists():
            try:
                prompt_path.unlink()
            except Exception as e:
                errors.append(f"Failed to delete {prompt_path}: {str(e)}")
        else:
            errors.append(f"Prompt file not found: {prompt_path}")

        if errors:
            return "; ".join(errors)

        return None
