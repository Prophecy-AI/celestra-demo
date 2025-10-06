"""Prehook factory functions for tool validation"""
from typing import Dict, List
from .path_validator import PathValidator, SecurityError


def create_path_validation_prehook(workspace_dir: str, path_params: List[str] = None):
    """
    Factory: Create path validation prehook for filesystem tools

    Args:
        workspace_dir: Workspace directory to validate against
        path_params: List of param names to validate (default: ["file_path", "path"])

    Returns:
        Async prehook function that validates and normalizes paths

    Example:
        hook = create_path_validation_prehook("/workspace/session123")
        agent.tools.set_prehook("Read", hook)
        agent.tools.set_prehook("Write", hook)
    """
    if path_params is None:
        path_params = ["file_path", "path"]

    validator = PathValidator(workspace_dir)

    async def prehook(input: Dict) -> None:
        """Validate and normalize file paths in input"""
        for param in path_params:
            if param in input:
                # Validate and normalize - modifies input in-place
                input[param] = validator.validate(input[param], "access")

    return prehook


def create_bash_warning_prehook():
    """
    Factory: Create prehook that warns Bash tool about workspace escapes

    Returns:
        Async prehook function that modifies bash command description

    Example:
        hook = create_bash_warning_prehook()
        agent.tools.set_prehook("Bash", hook)
    """
    async def prehook(input: Dict) -> None:
        """Add workspace boundary reminder to bash commands"""
        # No validation, just a reminder (bash is hard to sandbox)
        # The tool schema itself will have the warning
        pass

    return prehook
