"""
Base tool abstract class for Agent V5
"""
from abc import ABC, abstractmethod
from typing import Dict


class BaseTool(ABC):
    """Abstract base class for all tools"""

    def __init__(self, workspace_dir: str):
        """
        Initialize tool with workspace directory

        Args:
            workspace_dir: Path to workspace directory where tool operates
        """
        self.workspace_dir = workspace_dir

    @property
    @abstractmethod
    def name(self) -> str:
        """Return tool name"""
        pass

    @property
    @abstractmethod
    def schema(self) -> Dict:
        """
        Return Anthropic API compatible tool schema

        Returns:
            Dict with keys: name, description, input_schema
        """
        pass

    @abstractmethod
    async def execute(self, input: Dict) -> Dict:
        """
        Execute tool with given input

        Args:
            input: Tool input parameters as dict

        Returns:
            Dict with keys:
                - content (str): Tool output text
                - is_error (bool): Whether execution resulted in error
        """
        pass
