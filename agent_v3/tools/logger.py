"""
Debug logging utility for tools
"""
import os
import time

# ANSI color codes for dimmed output
DIM = "\033[2m"
RESET = "\033[0m"
CYAN_DIM = "\033[2;36m"
YELLOW_DIM = "\033[2;33m"
GREEN_DIM = "\033[2;32m"
RED_DIM = "\033[2;31m"


def tool_log(tool_name: str, message: str, level: str = "info"):
    """Log tool execution details when DEBUG=1"""
    if os.getenv("DEBUG", "0") != "1":
        return

    timestamp = time.strftime("%H:%M:%S")

    # Color based on level
    if level == "error":
        color = RED_DIM
    elif level == "success":
        color = GREEN_DIM
    elif level == "sql":
        color = CYAN_DIM
    else:
        color = DIM

    print(f"{color}[{timestamp}] [{tool_name}] {message}{RESET}")