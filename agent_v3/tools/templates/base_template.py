"""
Base template class for tool generation
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class ToolTemplate(ABC):
    """Base class for tool templates"""

    @abstractmethod
    def generate_tool_code(self, config: Dict[str, Any]) -> str:
        """
        Generate Python code for the tool

        Args:
            config: Configuration dictionary with tool-specific parameters

        Returns:
            Python code as a string
        """
        pass

    @abstractmethod
    def generate_prompt(self, config: Dict[str, Any]) -> str:
        """
        Generate YAML prompt for the tool

        Args:
            config: Configuration dictionary with tool-specific parameters

        Returns:
            YAML prompt as a string
        """
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> Optional[str]:
        """
        Validate configuration dictionary

        Args:
            config: Configuration to validate

        Returns:
            Error message if invalid, None if valid
        """
        pass

    @abstractmethod
    def get_config_schema(self) -> Dict[str, Any]:
        """
        Get the expected configuration schema

        Returns:
            Dictionary describing expected fields and their types
        """
        pass
