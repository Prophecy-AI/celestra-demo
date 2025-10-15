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
        self._custom_prehook = None

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

    async def prehook(self, input: Dict) -> None:
        """
        Pre-execution hook for validation and input normalization

        Calls custom prehook if set via set_custom_prehook().
        Can modify input dict in-place (e.g., normalize paths).

        Args:
            input: Tool input parameters as dict

        Raises:
            Exception: If validation fails
        """
        if self._custom_prehook:
            await self._custom_prehook(input)

    def set_custom_prehook(self, hook_fn):
        """
        Set custom prehook function

        Args:
            hook_fn: async function(input: Dict) -> None
        """
        self._custom_prehook = hook_fn

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
