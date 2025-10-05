"""
Context management for agent_v3 - Simplified state tracking
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
import time
import polars as pl


@dataclass
class ToolExecution:
    """Record of a single tool execution"""
    tool_name: str
    parameters: Dict[str, Any]
    result: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    error: Optional[str] = None


class Context:
    """
    Simplified context for recursive agent flow.
    Thread-safety removed as we're using sequential execution.
    """

    def __init__(self, session_id: str, io_handler=None):
        self.session_id = session_id
        self.io_handler = io_handler  # Optional IO handler for WebSocket mode
        self.conversation_history: List[Dict[str, str]] = []
        self.tool_history: List[ToolExecution] = []
        self.dataframes: Dict[str, pl.DataFrame] = {}
        self.queries: Dict[str, str] = {}
        self.csv_paths: Dict[str, str] = {}
        self.system_hints: List[str] = []
        self.recursion_depth = 0
        self.max_depth = 30
        self.created_at = datetime.now()
        self.original_user_query: Optional[str] = None  # Store original query for evaluations

    def add_user_message(self, content: str) -> None:
        """Add user message to conversation history"""
        self.conversation_history.append({
            "role": "user",
            "content": content,
            "timestamp": time.time()
        })

    def add_assistant_message(self, content: str) -> None:
        """Add assistant message to conversation history"""
        self.conversation_history.append({
            "role": "assistant",
            "content": content,
            "timestamp": time.time()
        })

    def add_tool_execution(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Dict[str, Any]
    ) -> None:
        """Record tool execution"""
        execution = ToolExecution(
            tool_name=tool_name,
            parameters=parameters,
            result=result
        )
        self.tool_history.append(execution)

        # Add to conversation as assistant context
        self.conversation_history.append({
            "role": "assistant",
            "content": f"Tool: {tool_name}\nResult: {result}",
            "timestamp": time.time()
        })

    def add_tool_error(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        error: str
    ) -> None:
        """Record tool execution error"""
        execution = ToolExecution(
            tool_name=tool_name,
            parameters=parameters,
            result={},
            error=error
        )
        self.tool_history.append(execution)

    def store_dataframe(
        self,
        name: str,
        df: pl.DataFrame,
        sql: str,
        csv_path: str
    ) -> None:
        """Store DataFrame with associated metadata"""
        self.dataframes[name] = df
        self.queries[name] = sql
        self.csv_paths[name] = csv_path

    def get_dataframe(self, name: str) -> Optional[pl.DataFrame]:
        """Retrieve stored DataFrame"""
        return self.dataframes.get(name)

    def get_all_datasets(self) -> List[Dict[str, Any]]:
        """Get metadata for all stored datasets"""
        datasets = []
        for name, df in self.dataframes.items():
            datasets.append({
                "name": name,
                "shape": df.shape,
                "columns": df.columns,
                "sql": self.queries.get(name, ""),
                "csv_path": self.csv_paths.get(name, "")
            })
        return datasets

    def get_last_tool_name(self) -> Optional[str]:
        """Get the name of the last executed tool"""
        if self.tool_history:
            return self.tool_history[-1].tool_name
        return None

    def get_last_tool_result(self) -> Dict[str, Any]:
        """Get the result of the last executed tool"""
        if self.tool_history:
            return self.tool_history[-1].result
        return {}

    def get_last_tool_execution(self) -> Optional[ToolExecution]:
        """Get the last tool execution record (for hint generation)"""
        if self.tool_history:
            return self.tool_history[-1]
        return None

    def has_error(self) -> bool:
        """Check if the last tool execution had an error"""
        if self.tool_history:
            return self.tool_history[-1].error is not None
        return False

    def add_system_hint(self, hint: str) -> None:
        """Add a system hint for the LLM"""
        self.system_hints.append(hint)

    def get_system_hints(self) -> List[str]:
        """Get and clear system hints"""
        hints = self.system_hints.copy()
        self.system_hints.clear()
        return hints

    def increment_depth(self) -> bool:
        """
        Increment recursion depth.
        Returns True if within limits, False if max depth reached.
        """
        self.recursion_depth += 1
        return self.recursion_depth < self.max_depth

    def get_conversation_for_llm(self) -> List[Dict[str, str]]:
        """
        Get conversation history formatted for LLM.
        Includes token limiting and hint injection.
        """
        messages = []

        # Add recent conversation (last 20 exchanges to avoid token limits)
        recent_history = self.conversation_history[-40:] if len(self.conversation_history) > 40 else self.conversation_history

        for msg in recent_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        # Add system hints if any
        hints = self.get_system_hints()
        if hints:
            messages.append({
                "role": "user",
                "content": f"<system-reminder>\n{chr(10).join(hints)}\n</system-reminder>"
            })

        return messages

    def get_summary(self) -> Dict[str, Any]:
        """Get execution summary"""
        return {
            "session_id": self.session_id,
            "total_tools_executed": len(self.tool_history),
            "datasets_created": len(self.dataframes),
            "dataset_names": list(self.dataframes.keys()),
            "total_rows": sum(df.shape[0] for df in self.dataframes.values()),
            "recursion_depth": self.recursion_depth,
            "errors": [t for t in self.tool_history if t.error],
            "duration": time.time() - self.created_at.timestamp()
        }