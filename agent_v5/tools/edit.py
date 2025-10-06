"""
Edit tool for exact string replacement in files
"""
import os
from typing import Dict
from .base import BaseTool


class EditTool(BaseTool):
    """Replace exact strings in files"""

    @property
    def name(self) -> str:
        return "Edit"

    @property
    def schema(self) -> Dict:
        return {
            "name": "Edit",
            "description": "Replace exact string in file",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to file"
                    },
                    "old_string": {
                        "type": "string",
                        "description": "Exact string to find"
                    },
                    "new_string": {
                        "type": "string",
                        "description": "String to replace with"
                    },
                    "replace_all": {
                        "type": "boolean",
                        "description": "Replace all occurrences (default false)",
                        "default": False
                    }
                },
                "required": ["file_path", "old_string", "new_string"]
            }
        }

    async def execute(self, input: Dict) -> Dict:
        file_path = input["file_path"]
        old_string = input["old_string"]
        new_string = input["new_string"]
        replace_all = input.get("replace_all", False)

        try:
            if not file_path.startswith('/'):
                file_path = os.path.join(self.workspace_dir, file_path)

            with open(file_path, 'r') as f:
                content = f.read()

            if old_string not in content:
                return {
                    "content": f"String not found in file: {old_string}",
                    "is_error": True
                }

            if not replace_all and content.count(old_string) > 1:
                return {
                    "content": f"String appears {content.count(old_string)} times. Use replace_all=true or provide more context.",
                    "is_error": True
                }

            if replace_all:
                new_content = content.replace(old_string, new_string)
            else:
                new_content = content.replace(old_string, new_string, 1)

            with open(file_path, 'w') as f:
                f.write(new_content)

            lines = new_content.split('\n')
            snippet = "(edit applied, no preview available)"
            for i, line in enumerate(lines):
                if new_string in line:
                    start = max(0, i - 2)
                    end = min(len(lines), i + 3)
                    snippet_lines = lines[start:end]
                    snippet = "\n".join([f"{j+start+1:6d}→{l}" for j, l in enumerate(snippet_lines)])
                    break

            return {
                "content": f"The file {file_path} has been updated. Here's the result:\n{snippet}",
                "is_error": False
            }

        except FileNotFoundError:
            return {
                "content": f"File not found: {file_path}",
                "is_error": True
            }
        except Exception as e:
            return {
                "content": f"Error editing file: {str(e)}",
                "is_error": True
            }
