import os
from pathlib import Path
from dotenv import load_dotenv

# Load from .env in jarvis directory first
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# --- Gemini API ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# --- Chrome CDP ---
CHROME_PATH = os.getenv(
    "CHROME_PATH",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
)
CDP_PORT = int(os.getenv("CDP_PORT", "9222"))
CHROME_PROFILE_DIR = os.getenv(
    "CHROME_PROFILE_DIR",
    r"C:\ChromeJarvisProfile",
)

# --- User Profile (for LLM content generation) ---
USER_PROFILE = {
    "name": os.getenv("USER_NAME", "BlenSpark"),
    "title": os.getenv("USER_TITLE", "AI Automation Expert"),
    "company": os.getenv("USER_COMPANY", "BlenSpark"),
    "skills": os.getenv(
        "USER_SKILLS",
        "AI voice agents, Django, Python, Gemini Live API, full-stack development",
    ).split(", "),
    "bio": os.getenv(
        "USER_BIO",
        "Full-stack AI developer at BlenSpark. Built Sara — an AI voice agent "
        "for healthcare and restaurant automation using Gemini Live API, Django, "
        "and ElevenLabs TTS. Expert in browser automation, agentic AI systems, "
        "and real-time voice-to-voice applications.",
    ),
    "resume_path": os.getenv("RESUME_PATH", ""),
}

# --- Daily Rate Limits (anti-detection) ---
RATE_LIMITS = {
    "linkedin_connections_per_day": int(os.getenv("LINKEDIN_CONN_LIMIT", "25")),
    "linkedin_applications_per_day": int(os.getenv("LINKEDIN_APP_LIMIT", "10")),
    "upwork_proposals_per_day": int(os.getenv("UPWORK_PROP_LIMIT", "15")),
    "min_delay_seconds": float(os.getenv("MIN_DELAY", "1.5")),
    "max_delay_seconds": float(os.getenv("MAX_DELAY", "4.0")),
}

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
    "linkedin": {
        "module": "jarvis.apps.linkedin",
        "class": "LinkedInAgent",
        "description": "LinkedIn lead gen, profile visits, connection requests, job search, Easy Apply",
    },
    "upwork": {
        "module": "jarvis.apps.upwork",
        "class": "UpworkAgent",
        "description": "Upwork job search, proposal submission, messages, contracts",
    },
    "youtube": {
        "module": "jarvis.apps.youtube",
        "class": "YouTubeAgent",
        "description": "YouTube search, watch videos, post comments, browse channels",
    },
    "whatsapp": {
        "module": "jarvis.apps.whatsapp",
        "class": "WhatsAppWeb",
        "description": "WhatsApp Web messaging, read chats, send files",
    },
    "gmail": {
        "module": "jarvis.apps.gmail",
        "class": "GmailWeb",
        "description": "Gmail compose, search, read inbox, open emails",
    },
    "content_gen": {
        "module": "jarvis.agent.content_gen",
        "class": "ContentGenerator",
        "description": "LLM-powered cover letters, connection notes, job scoring",
    },
    "pipeline": {
        "module": "jarvis.apps.pipelines",
        "class": "AutomationPipelines",
        "description": "Full automation workflows: Upwork outreach, LinkedIn lead gen, email triage",
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
