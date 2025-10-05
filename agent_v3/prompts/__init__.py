"""
Prompts package for agent_v3
"""
from .system_prompt import MAIN_SYSTEM_PROMPT, get_main_system_prompt
from . import hints

__all__ = ["MAIN_SYSTEM_PROMPT", "get_main_system_prompt", "hints"]
