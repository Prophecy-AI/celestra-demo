"""
Prompts package for agent_v3
"""

from .system_prompt import MAIN_SYSTEM_PROMPT
from .loader import PromptLoader

__all__ = ["MAIN_SYSTEM_PROMPT", "PromptLoader"]