import asyncio
import json
import logging
from typing import Callable

import jarvis.config as cfg
from jarvis.tools.file_manager import FileManager
from jarvis.tools.browser import Browser
from jarvis.tools.desktop import Desktop
from jarvis.tools.terminal import Terminal

logger = logging.getLogger(__name__)


# Safety: reject obviously destructive commands
_DESTRUCTIVE_PATTERNS = [
    "format",
    "del /s /q",
    "rd /s /q",
    "rm -rf /",
    "shutdown /r",
    "shutdown /s",
]


class ToolRouter:
    """Maps Gemini's structured tool_calls to actual tool execution."""

    def __init__(self, callback: Callable | None = None):
        """callback: optional async fn(event_type, data) for streaming."""
        self.file_manager = FileManager()
        self.browser = Browser()
        self.desktop = Desktop()
        self.terminal = Terminal()
        self.callback = callback

        # App agents — lazy-initialized on first use
        self._linkedin = None
        self._upwork = None
        self._youtube = None
        self._whatsapp = None
        self._gmail = None
        self._content_gen = None
        self._pipeline = None

    def _get_app_agent(self, name: str):
        """Lazy-load app agents to avoid import overhead when not needed."""
        if name == "linkedin":
            if self._linkedin is None:
                from jarvis.apps.linkedin import LinkedInAgent
                self._linkedin = LinkedInAgent()
            return self._linkedin

        elif name == "upwork":
            if self._upwork is None:
                from jarvis.apps.upwork import UpworkAgent
                self._upwork = UpworkAgent()
            return self._upwork

        elif name == "youtube":
            if self._youtube is None:
                from jarvis.apps.youtube import YouTubeAgent
                self._youtube = YouTubeAgent()
            return self._youtube

        elif name == "whatsapp":
            if self._whatsapp is None:
                from jarvis.apps.whatsapp import WhatsAppWeb
                self._whatsapp = WhatsAppWeb()
            return self._whatsapp

        elif name == "gmail":
            if self._gmail is None:
                from jarvis.apps.gmail import GmailWeb
                self._gmail = GmailWeb()
            return self._gmail

        elif name == "content_gen":
            if self._content_gen is None:
                from jarvis.agent.content_gen import ContentGenerator
                self._content_gen = ContentGenerator()
            return self._content_gen

        elif name == "pipeline":
            if self._pipeline is None:
                from jarvis.apps.pipelines import AutomationPipelines
                self._pipeline = AutomationPipelines()
            return self._pipeline

        return None

    async def _emit(self, event_type: str, data: dict):
        if self.callback:
            await self.callback(event_type, data)

    async def execute_plan(self, plan: dict) -> list[dict]:
        """Execute a Gemini plan (thought + tool_calls list). Returns results."""
        results = []
        thought = plan.get("thought", "")
        tool_calls = plan.get("tool_calls", [])

        if not tool_calls:
            return results

        await self._emit("thinking", {"thought": thought})

        for i, call in enumerate(tool_calls, start=1):
            tool_name = call.get("tool", "")
            action = call.get("action", "")
            params = call.get("params", {})
            full_method = f"{tool_name}.{action}"

            # Safety check
            if self._is_destructive(tool_name, action, params):
                await self._emit("safety_block", f"Blocked destructive action: {full_method}")
                results.append({"index": i, "tool": full_method, "success": False, "error": "Safety: blocked destructive action"})
                continue

            await self._emit("tool_start", {"index": i, "tool": full_method, "params": params})

            try:
                result = await self._invoke(tool_name, action, params)
                success = result.get("success", False)
                await self._emit(
                    "tool_result",
                    {"index": i, "tool": full_method, "success": success, "output": str(result.get("output", ""))},
                )
                results.append({"index": i, "tool": full_method, "success": success, "output": result.get("output"), "error": result.get("error")})
            except Exception as e:
                logger.error(f"Tool execution failed: {full_method} — {e}")
                await self._emit("tool_error", {"index": i, "tool": full_method, "error": str(e)})
                results.append({"index": i, "tool": full_method, "success": False, "error": str(e)})

        return results

    async def _invoke(self, tool_name: str, action: str, params: dict) -> dict:
        """Dynamically call a tool method."""
        # Core tools
        core_map = {
            "file_manager": self.file_manager,
            "browser": self.browser,
            "desktop": self.desktop,
            "terminal": self.terminal,
        }

        tool = core_map.get(tool_name)

        # If not a core tool, try app agents
        if tool is None:
            tool = self._get_app_agent(tool_name)

        if not tool:
            return {"success": False, "output": None, "error": f"Unknown tool: {tool_name}"}

        method = getattr(tool, action, None)
        if not method:
            return {"success": False, "output": None, "error": f"Unknown action '{action}' on tool '{tool_name}'"}

        # Run sync tools in a thread to not block the event loop
        if asyncio.iscoroutinefunction(method):
            return await method(**params)
        else:
            return await asyncio.to_thread(method, **params)

    def _is_destructive(self, tool_name: str, action: str, params: dict) -> bool:
        """Check if a tool call is potentially destructive."""
        if tool_name == "terminal":
            cmd = params.get("command", "").lower()
            return any(pat in cmd for pat in _DESTRUCTIVE_PATTERNS)
        if tool_name == "file_manager" and action == "delete_file":
            path = params.get("path", "").lower()
            # Block deletion of critical system directories
            system_paths = ["c:\\windows", "c:\\program files", "c:\\program files (x86)"]
            return any(path.startswith(sp) for sp in system_paths)
        return False

    async def cleanup(self):
        """Release resources."""
        await self.browser.close()
        # CDP connection is shared/singleton — don't close it here
