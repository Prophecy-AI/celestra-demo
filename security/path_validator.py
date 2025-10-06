"""Path validation to prevent workspace escapes"""
import os


class SecurityError(Exception):
    """Raised when security violation detected"""
    pass


class PathValidator:
    """Validate file paths are within workspace boundaries"""

    def __init__(self, workspace_dir: str):
        """Initialize validator with workspace directory

        Args:
            workspace_dir: Absolute path to workspace directory
        """
        self.workspace_dir = os.path.realpath(workspace_dir)

    def validate(self, path: str, operation: str = "access") -> str:
        """Resolve and validate path is within workspace

        Args:
            path: File path to validate (relative or absolute)
            operation: Operation name for error message

        Returns:
            Resolved absolute path within workspace

        Raises:
            SecurityError: If path escapes workspace boundaries
        """
        # Resolve relative paths against workspace
        if not path.startswith('/'):
            resolved = os.path.realpath(os.path.join(self.workspace_dir, path))
        else:
            resolved = os.path.realpath(path)

        # Check if resolved path is within workspace
        # Use realpath to handle symlinks and .. sequences
        if not resolved.startswith(self.workspace_dir + os.sep) and resolved != self.workspace_dir:
            raise SecurityError(
                f"Access denied: {operation} outside workspace. "
                f"Path: {path} -> {resolved}, Workspace: {self.workspace_dir}"
            )

        return resolved
