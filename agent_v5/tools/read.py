"""
Read tool for reading file contents
"""
import os
from typing import Dict
from .base import BaseTool


class ReadTool(BaseTool):
    """Read file contents from workspace"""

    @property
    def name(self) -> str:
        return "Read"

    @property
    def schema(self) -> Dict:
        return {
            "name": "Read",
            "description": "Read file contents from workspace",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to file"
                    },
                    "offset": {
                        "type": "number",
                        "description": "Line number to start reading from"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Number of lines to read"
                    }
                },
                "required": ["file_path"]
            }
        }

    async def execute(self, input: Dict) -> Dict:
        file_path = input["file_path"]
        offset = input.get("offset", 0)
        limit = input.get("limit", 2000)

        try:
            if not file_path.startswith('/'):
                file_path = os.path.join(self.workspace_dir, file_path)

            with open(file_path, 'r') as f:
                lines = f.readlines()

            selected_lines = lines[offset:offset + limit]

            numbered_lines = []
            for i, line in enumerate(selected_lines, start=offset + 1):
                if len(line) > 2000:
                    line = line[:2000] + "... (line truncated)\n"
                numbered_lines.append(f"{i:6d}→{line}")

            content = "".join(numbered_lines)

            if not content.strip():
                content = "<system-reminder>\nThis file exists but is empty.\n</system-reminder>"

            return {
                "content": content,
                "is_error": False,
                "debug_summary": f"{len(selected_lines)} lines, {sum(len(l) for l in selected_lines)} bytes"
            }

        except FileNotFoundError:
            return {
                "content": f"File not found: {file_path}",
                "is_error": True
            }
        except Exception as e:
            return {
                "content": f"Error reading file: {str(e)}",
                "is_error": True
            }
