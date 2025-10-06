"""
TodoWrite tool for task list management
"""
from typing import Dict, List
from .base import BaseTool


class TodoWriteTool(BaseTool):
    """Create and update task lists"""

    def __init__(self, workspace_dir: str):
        super().__init__(workspace_dir)
        self.todos: List[Dict] = []

    @property
    def name(self) -> str:
        return "TodoWrite"

    @property
    def schema(self) -> Dict:
        return {
            "name": "TodoWrite",
            "description": "Create and update task list",
            "input_schema": {
                "type": "object",
                "properties": {
                    "todos": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {
                                    "type": "string",
                                    "description": "Task description (imperative form)"
                                },
                                "activeForm": {
                                    "type": "string",
                                    "description": "Present continuous form (e.g., 'Running tests')"
                                },
                                "status": {
                                    "type": "string",
                                    "enum": ["pending", "in_progress", "completed"],
                                    "description": "Task status"
                                }
                            },
                            "required": ["content", "activeForm", "status"]
                        }
                    }
                },
                "required": ["todos"]
            }
        }

    async def execute(self, input: Dict) -> Dict:
        self.todos = input["todos"]

        in_progress_count = sum(1 for t in self.todos if t["status"] == "in_progress")

        if in_progress_count > 1:
            return {
                "content": "Warning: More than one task marked as in_progress. Only one task should be in_progress at a time.",
                "is_error": False
            }

        return {
            "content": "Todos have been modified successfully. Ensure that you continue to use the todo list to track your progress. Please proceed with the current tasks if applicable",
            "is_error": False
        }
