"""
Glob tool for file pattern matching
"""
import os
import glob as glob_module
from typing import Dict
from .base import BaseTool


class GlobTool(BaseTool):
    """Find files matching glob patterns"""

    @property
    def name(self) -> str:
        return "Glob"

    @property
    def schema(self) -> Dict:
        return {
            "name": "Glob",
            "description": "Find files matching glob pattern",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern (e.g., '**/*.py')"
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search in (default: workspace)"
                    }
                },
                "required": ["pattern"]
            }
        }

    async def execute(self, input: Dict) -> Dict:
        pattern = input["pattern"]
        search_path = input.get("path", self.workspace_dir)

        try:
            if not search_path.startswith('/'):
                search_path = os.path.join(self.workspace_dir, search_path)

            full_pattern = os.path.join(search_path, pattern)

            matches = glob_module.glob(full_pattern, recursive=True)

            matches.sort(key=lambda x: os.path.getmtime(x), reverse=True)

            if not matches:
                return {
                    "content": "No files found",
                    "is_error": False
                }

            return {
                "content": "\n".join(matches),
                "is_error": False,
                "debug_summary": f"Found {len(matches)} files, first 5: {matches[:5]}"
            }

        except Exception as e:
            return {
                "content": f"Error globbing: {str(e)}",
                "is_error": True
            }
