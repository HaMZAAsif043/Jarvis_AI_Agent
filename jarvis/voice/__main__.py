"""Voice mode entry point for JARVIS."""
import argparse
import json
import logging
import sys

import numpy as np
import sounddevice as sd

from google.genai import Client
from google.genai.types import (
    FunctionDeclaration,
    Tool as GenAITool,
    LiveConnectConfig,
)

# Import tool instances
from jarvis.tools.file_manager import FileManager
from jarvis.tools.browser import Browser
from jarvis.tools.desktop import Desktop
from jarvis.tools.terminal import Terminal

from jarvis.voice import (
    SAMPLE_RATE,
    CHUNK_SIZE,
    SAMPLE_RATE as _sr,
    MicStream,
    play_audio,
    _execute_voice_tool_call,
    _build_function_declarations,
)

logger = logging.getLogger(__name__)

VOICE_SYSTEM_PROMPT = """\
You are JARVIS, an AI desktop assistant with full PC control.
You can use tools (file_manager, browser, desktop, terminal) to accomplish tasks.
You are speaking with the user via voice-to-voice real-time audio.
Be natural, concise, and conversational in your responses.
When the user asks you to do something on their PC, use the appropriate tools.
Do NOT narrate every step when executing tools silently — just confirm when the task is done.
If a tool fails, adapt or explain and try an alternative approach.
"""


async def run_voice():
    """Real-time voice conversation using Gemini Live API."""
    import jarvis.config as cfg

    if not cfg.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not set. Set it in .env.")
        sys.exit(1)

    model_name = cfg.GEMINI_MODEL or "gemini-2.5-flash-live-preview"

    print("=" * 60)
    print("  JARVIS AI — Voice Mode")
    print(f"  Model: {model_name}")
    print("  Speak naturally — Gemini streams audio in real-time")
    print("  Press Ctrl+C to stop")
    print("=" * 60)

    client = Client(api_key=cfg.GEMINI_API_KEY)
    tools = {
        "file_manager": FileManager(),
        "browser": Browser(),
        "desktop": Desktop(),
        "terminal": Terminal(),
    }

    declarations = _build_function_declarations()
    genai_tool = GenAITool(function_declarations=declarations)

    config = LiveConnectConfig(
        response_modalities=["AUDIO", "TEXT"],
        system_instruction={"parts": [{"text": VOICE_SYSTEM_PROMPT}]},
        tools=[genai_tool],
    )

    # Audio playback event loop (runs in main thread)
    playback_event = asyncio.Event()
    playback_queue: asyncio.Queue[bytes | None] = asyncio.Queue()

    async def _playback_worker():
        """Play audio chunks from queue."""
        while True:
            chunk = await playback_queue.get()
            if chunk is None:  # sentinel
                break
            play_audio(chunk)

    async def _handle_server_message(session, playback_queue):
        """Process messages received from Gemini Live API."""
        async for message in session.receive():
            # Server content with audio + text
            if message.server_content is not None:
                sc = message.server_content

                # Audio output
                model_turn = sc.model_turn or sc.input_transcription or sc.output_transcription
                if model_turn is not None:
                    # Check for audio in model_turn
                    for part in model_turn.parts or []:
                        if part.inline_data is not None:
                            data = part.inline_data.data
                            if data:
                                await playback_queue.put(data)

                # Handle function calls
                if sc.tool_calls:
                    responses = []
                    for tc in sc.tool_calls:
                        # tool_type should have function_call info
                        if tc.tool_type.function_call is not None:
                            fc = tc.tool_type.function_call
                            result = await _execute_voice_tool_call(
                                fc.name, fc.args or {}, tools
                            )
                            responses.append(
                                {"name": fc.name, "response": {"parts": [{"text": json.dumps(result)}]}, "id": fc.id}
                            )

                    if responses:
                        await session.send_tool_response(
                            function_responses=[
                                {"name": r["name"], "response": r["response"], "id": r["id"]}
                                for r in responses
                            ]
                        )

                if sc.turn_complete:
                    await playback_queue.put(None)  # signal done

            # Standalone tool calls (not wrapped in server_content)
            if message.tool_call:
                responses = []
                for tc in [message.tool_call]:
                    if tc.tool_type.function_call is not None:
                        fc = tc.tool_type.function_call
                        result = await _execute_voice_tool_call(
                            fc.name, fc.args or {}, tools
                        )
                        responses.append(
                            {"name": fc.name, "response": {"parts": [{"text": json.dumps(result)}]}, "id": fc.id}
                        )
                if responses:
                    await session.send_tool_response(
                        function_responses=[
                            {"name": r["name"], "response": r["response"], "id": r["id"]}
                            for r in responses
                        ]
                    )

            # Voice detection (when Gemini detects user is speaking)
            if message.voice_activity:
                pass  # Could pause playback here

    print(f"\n  Listening... (speak your command)")

    async with client.aio.live.connect(
        model=model_name,
        config=config,
    ) as session:
        # Start audio capture
        async with MicStream() as mic:
            # Start playback worker
            playback_task = asyncio.create_task(_playback_worker())

            # Forward mic audio to Gemini
            async for chunk in mic:
                await session.send_realtime_input(audio=chunk)

            playback_task.cancel()
