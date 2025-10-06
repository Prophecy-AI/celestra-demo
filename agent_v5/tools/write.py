"""
Write tool for creating and overwriting files
"""
import os
from typing import Dict
from .base import BaseTool


class WriteTool(BaseTool):
    """Write content to files in workspace"""

    @property
    def name(self) -> str:
        return "Write"

    @property
    def schema(self) -> Dict:
        return {
            "name": "Write",
            "description": "Write content to a file (creates or overwrites)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to file"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write"
                    }
                },
                "required": ["file_path", "content"]
            }
        }

    async def execute(self, input: Dict) -> Dict:
        file_path = input["file_path"]
        content = input["content"]

        try:
            if not file_path.startswith('/'):
                file_path = os.path.join(self.workspace_dir, file_path)

            file_exists = os.path.exists(file_path)

            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, 'w') as f:
                f.write(content)

            if file_exists:
                message = f"File updated successfully at: {file_path}"
            else:
                message = f"File created successfully at: {file_path}"

            return {
                "content": message,
                "is_error": False,
                "debug_summary": f"{len(content)} bytes, {content.count(chr(10))+1} lines"
            }

        except Exception as e:
            return {
                "content": f"Error writing file: {str(e)}",
                "is_error": True
            }
