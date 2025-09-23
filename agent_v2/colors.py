"""
Simple color constants for terminal output
"""

# ANSI color codes
RESET = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'

# Colors
BLACK = '\033[30m'
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
BLUE = '\033[34m'
MAGENTA = '\033[35m'
CYAN = '\033[36m'
WHITE = '\033[37m'
GRAY = '\033[90m'

# Bright colors
BRIGHT_RED = '\033[91m'
BRIGHT_GREEN = '\033[92m'
BRIGHT_YELLOW = '\033[93m'
BRIGHT_BLUE = '\033[94m'
BRIGHT_MAGENTA = '\033[95m'
BRIGHT_CYAN = '\033[96m'

# Semantic colors for logging - using bright colors with DIM for better effect
# DIM works better with bright colors than regular ones
TIMESTAMP = f"{DIM}{GRAY}"  # Gray is already dim
COMPONENT = f"{DIM}{BRIGHT_CYAN}"
PROCESS = f"{DIM}{BRIGHT_BLUE}"
SUCCESS = f"{DIM}{BRIGHT_GREEN}"
WARNING = f"{DIM}{BRIGHT_YELLOW}"
ERROR = f"{DIM}{BRIGHT_RED}"
DATA = f"{DIM}{BRIGHT_MAGENTA}"
SQL = f"{DIM}{BRIGHT_CYAN}"