import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Gemini API ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# --- Server ---
HOST = os.getenv("JARVIS_HOST", "127.0.0.1")
PORT = int(os.getenv("JARVIS_PORT", "8000"))

# --- Paths ---
PROJECT_DIR = Path(__file__).parent
LOGS_DIR = PROJECT_DIR / "logs"
MEMORY_DB = PROJECT_DIR / "jarvis_memory.db"
LOGS_DIR.mkdir(exist_ok=True)

# --- Tool Registry ---
TOOLS = {
    "file_manager": {
        "module": "jarvis.tools.file_manager",
        "class": "FileManager",
        "description": "Read, write, copy, move, delete, search files and directories",
    },
    "browser": {
        "module": "jarvis.tools.browser",
        "class": "Browser",
        "description": "Open URLs, click elements, fill forms, take screenshots, extract page text",
    },
    "desktop": {
        "module": "jarvis.tools.desktop",
        "class": "Desktop",
        "description": "Mouse/keyboard control, screenshots, window management",
    },
    "terminal": {
        "module": "jarvis.tools.terminal",
        "class": "Terminal",
        "description": "Execute shell commands with timeout",
    },
}

# --- Dangerous commands blocked by default ---
BLOCKED_COMMANDS = [
    "format",
    "del /s /q",
    "rd /s /q",
    "rm -rf",
    "> /dev/sda",
    "shutdown /r",
    "shutdown /s",
]

# --- Scheduler defaults ---
SCHEDULER_TASKS = [
    # Example: {"name": "system_check", "cron": "0 9 * * 1-5", "action": "Run diagnostic and log to jarvis.log"}
]

# --- Execution loop ---
MAX_ITERATIONS = int(os.getenv("JARVIS_MAX_ITERATIONS", "15"))
