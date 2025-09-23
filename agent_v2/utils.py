"""
Utility functions for colored logging
"""
import os

# ANSI color codes
GREY = '\033[90m'
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
MAGENTA = '\033[95m'
CYAN = '\033[96m'
WHITE = '\033[97m'
RESET = '\033[0m'
DIM = '\033[2m'

def grey_log(message: str) -> str:
    """Format message in grey/dim for debug logs"""
    if os.getenv('DEBUG', '0') == '1':
        return f"{DIM}{GREY}{message}{RESET}"
    return message

def colored_log(message: str, color: str = GREY) -> str:
    """Format message with specified color"""
    if os.getenv('DEBUG', '0') == '1':
        return f"{color}{message}{RESET}"
    return message

def debug_print(message: str):
    """Print debug message in grey/dim"""
    if os.getenv('DEBUG', '0') == '1':
        print(grey_log(message))