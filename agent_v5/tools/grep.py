"""
Grep tool for searching file contents using ripgrep
"""
import asyncio
import os
from typing import Dict
from .base import BaseTool


class GrepTool(BaseTool):
    """Search file contents with regex using ripgrep"""

    @property
    def name(self) -> str:
        return "Grep"

    @property
    def schema(self) -> Dict:
        return {
            "name": "Grep",
            "description": "Search file contents with regex (ripgrep-based)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to search for"
                    },
                    "path": {
                        "type": "string",
                        "description": "File or directory to search (default: workspace)"
                    },
                    "glob": {
                        "type": "string",
                        "description": "Glob pattern to filter files (e.g., '*.py')"
                    },
                    "type": {
                        "type": "string",
                        "description": "File type filter (e.g., 'py', 'js')"
                    },
                    "-i": {
                        "type": "boolean",
                        "description": "Case insensitive search"
                    },
                    "-n": {
                        "type": "boolean",
                        "description": "Show line numbers"
                    },
                    "-A": {
                        "type": "number",
                        "description": "Lines of context after match"
                    },
                    "-B": {
                        "type": "number",
                        "description": "Lines of context before match"
                    },
                    "-C": {
                        "type": "number",
                        "description": "Lines of context around match"
                    },
                    "output_mode": {
                        "type": "string",
                        "enum": ["content", "files_with_matches", "count"],
                        "description": "Output mode (default: files_with_matches)"
                    },
                    "multiline": {
                        "type": "boolean",
                        "description": "Enable multiline mode"
                    },
                    "head_limit": {
                        "type": "number",
                        "description": "Limit output to first N results"
                    }
                },
                "required": ["pattern"]
            }
        }

    async def execute(self, input: Dict) -> Dict:
        pattern = input["pattern"]
        search_path = input.get("path", self.workspace_dir)
        output_mode = input.get("output_mode", "files_with_matches")

        try:
            if not search_path.startswith('/'):
                search_path = os.path.join(self.workspace_dir, search_path)

            rg_args = ["rg", pattern]

            if input.get("-i"):
                rg_args.append("-i")

            if input.get("-n") and output_mode == "content":
                rg_args.append("-n")

            if input.get("-A") and output_mode == "content":
                rg_args.extend(["-A", str(input["-A"])])
            if input.get("-B") and output_mode == "content":
                rg_args.extend(["-B", str(input["-B"])])
            if input.get("-C") and output_mode == "content":
                rg_args.extend(["-C", str(input["-C"])])

            if input.get("glob"):
                rg_args.extend(["--glob", input["glob"]])

            if input.get("type"):
                rg_args.extend(["--type", input["type"]])

            if input.get("multiline"):
                rg_args.extend(["-U", "--multiline-dotall"])

            if output_mode == "files_with_matches":
                rg_args.append("-l")
            elif output_mode == "count":
                rg_args.append("-c")

            rg_args.append(search_path)

            process = await asyncio.create_subprocess_exec(
                *rg_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 1:
                return {
                    "content": "No matches found",
                    "is_error": False
                }
            elif process.returncode != 0:
                return {
                    "content": stderr.decode(),
                    "is_error": True
                }

            output = stdout.decode()

            if input.get("head_limit"):
                lines = output.split('\n')
                output = '\n'.join(lines[:input["head_limit"]])

            return {
                "content": output,
                "is_error": False
            }

        except FileNotFoundError:
            return {
                "content": "ripgrep (rg) not found. Please install ripgrep.",
                "is_error": True
            }
        except Exception as e:
            return {
                "content": f"Error searching: {str(e)}",
                "is_error": True
            }
