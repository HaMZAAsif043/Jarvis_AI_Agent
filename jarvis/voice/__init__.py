"""JARVIS Voice Mode — Gemini Live API audio-to-audio streaming with tool calling."""
import asyncio
import json
import logging
import threading

import numpy as np
import sounddevice as sd

from google.genai.types import (
    FunctionDeclaration,
    Tool as GenAITool,
    LiveConnectConfig,
)

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = int(SAMPLE_RATE * 0.05)  # 50ms


def play_audio(pcm_bytes: bytes):
    """Play PCM16 audio at 16kHz mono."""
    audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    sd.play(audio, samplerate=SAMPLE_RATE)


def _build_function_declarations():
    """All tool function declarations for Gemini Live API."""
    declarations = []

    for tool_name, funcs in [
        ("file_manager", [
            ("read_file", "Read file contents", {"path": "Full file path"}),
            ("write_file", "Write content to file", {"path": "File path", "content": "Content to write"}),
            ("copy_file", "Copy a file or directory", {"source": "Source path", "destination": "Destination path"}),
            ("move_file", "Move a file or directory", {"source": "Source path", "destination": "Destination path"}),
            ("delete_file", "Delete a file or directory", {"path": "Path to delete"}),
            ("list_dir", "List directory contents", {"path": "Directory path"}),
            ("search_files", "Search for files by glob pattern recursively", {"path": "Search root path", "pattern": "Glob pattern like *.pdf"}),
        ]),
        ("browser", [
            ("open_url", "Navigate browser to URL", {"url": "URL to open"}),
            ("get_page_text", "Extract all visible text from current or given page", {"url": "Optional URL"}),
            ("click_element", "Click an element by CSS selector", {"selector": "CSS selector"}),
            ("fill_form", "Fill a form field", {"selector": "CSS selector", "value": "Value to fill"}),
            ("submit_form", "Click submit button on a form", {"button_selector": "Optional submit button selector", "url": "Optional URL"}),
            ("get_element_text", "Get text from a specific element", {"selector": "CSS selector"}),
            ("get_page_title", "Get current page title", {}),
            ("screenshot_browser", "Screenshot current page", {}),
            ("wait_browser", "Wait in browser", {"seconds": "Wait duration"}),
            ("go_back", "Go back in browser history", {}),
        ]),
        ("desktop", [
            ("mouse_click", "Click at screen coordinates", {"x": "X coordinate", "y": "Y coordinate", "button": "left or right"}),
            ("keyboard_type", "Type text at current cursor position", {"text": "Text to type"}),
            ("press_key", "Press a single key", {"key": "Key name"}),
            ("hotkey", "Press hotkey combination", {"keys": "Keys as array, e.g. ['ctrl', 'c']"}),
            ("screenshot", "Take desktop screenshot", {}),
            ("list_windows", "List all open window titles", {}),
            ("focus_window", "Focus or activate a window by title", {"title": "Window title substring"}),
            ("wait", "Wait N seconds", {"seconds": "Wait duration"}),
            ("get_cursor_position", "Get current mouse cursor position", {}),
        ]),
        ("terminal", [
            ("run", "Execute a shell command", {"command": "Command to execute"}),
        ]),
    ]:
        for name, desc, params in funcs:
            props = {k: {"type": "string"} for k in params}
            if params:
                params_schema = {"type": "object", "properties": props}
            else:
                params_schema = {"type": "object", "properties": {}}
            declarations.append(FunctionDeclaration(
                name=f"{tool_name}.{name}",
                description=desc,
                parameters=params_schema,
            ))

    return declarations


# ── Audio capture ─────────────────────────────────────────────

class MicStream:
    """Async iterator yielding PCM16 audio chunks from the microphone."""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate
        self._queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._stream = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._closed = False

    async def __aenter__(self):
        self._loop = asyncio.get_event_loop()
        self._closed = False
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=CHANNELS,
            dtype="int16",
            blocksize=CHUNK_SIZE,
            callback=self._callback,
        )
        self._stream.start()
        return self

    async def __aexit__(self, *args):
        self._closed = True
        if self._stream:
            self._stream.stop()
            self._stream.close()
        # Drain queue
        while not self._queue.empty():
            await self._queue.get()

    def _callback(self, indata, frames, time_info, status):
        if status:
            logger.warning(f"Audio stream: {status}")
        self._loop.call_soon_threadsafe(self._queue.put_nowait, bytes(indata))

    def __aiter__(self):
        return self

    async def __anext__(self):
        chunk = await self._queue.get()
        return chunk


# ── Tool execution integration ────────────────────────────────

async def _execute_voice_tool_call(function_name: str, function_args: dict, tools: dict) -> dict:
    """Execute a tool called via Gemini function calling during voice mode."""
    parts = function_name.split(".", 1)
    if len(parts) != 2:
        return {"error": f"Unknown function: {function_name}"}

    tool_name, action = parts[0], parts[1]
    tool = tools.get(tool_name)
    if not tool:
        return {"error": f"Unknown tool: {tool_name}"}

    method = getattr(tool, action, None)
    if not method:
        return {"error": f"Unknown action '{action}' on tool '{tool_name}'"}

    # Convert JSON string args to plain strings for Gemini (it sometimes sends int as string "5" for number fields)
    cleaned = {}
    for k, v in function_args.items():
        if isinstance(v, list):
            # Gemini sends arrays of strings for hotkey etc
            cleaned[k] = v
        elif isinstance(v, (dict,)):
            cleaned[k] = str(v)
        else:
            # Convert numbers, bools to their native types
            cleaned[k] = v

    try:
        if asyncio.iscoroutinefunction(method):
            result = await method(**cleaned)
        else:
            result = await asyncio.to_thread(method, **cleaned)
        return result
    except Exception as e:
        return {"success": False, "output": None, "error": str(e)}
