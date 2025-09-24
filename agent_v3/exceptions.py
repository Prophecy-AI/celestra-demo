"""
Custom exceptions for agent_v3
"""


class AgentException(Exception):
    """Base exception for all agent errors"""
    pass


class ConnectionLostError(AgentException):
    """Raised when WebSocket connection is lost - non-recoverable"""
    pass


class ToolExecutionError(AgentException):
    """Raised when a tool fails to execute - potentially recoverable"""
    pass


class MaxRecursionError(AgentException):
    """Raised when max recursion depth is reached"""
    pass