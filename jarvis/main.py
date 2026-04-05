import asyncio
import json
import logging
import sys
import threading
import time

import jarvis.config as cfg
from jarvis.agent.brain import Brain
from jarvis.agent.router import ToolRouter
from jarvis.agent.memory import Memory

# ── Logging: keep app logs, silence noisy third-party libs ────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Suppress verbose HTTP / SDK logs that overwrite the spinner
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.WARNING)
logging.getLogger("google_genai.models").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


# ── Spinner for CLI feedback ──────────────────────────────────
SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


def _spinner_task(active: list, label: str):
    """Simple terminal spinner in a background thread."""
    i = 0
    start = time.time()
    while active[0]:
        elapsed = time.time() - start
        frame = SPINNER_FRAMES[i % len(SPINNER_FRAMES)]
        sys.stdout.write(f"\r  {frame} {label} ({elapsed:.0f}s)")
        sys.stdout.flush()
        time.sleep(0.08)
        i += 1
    # Clear spinner line
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()


async def run_cli():
    """CLI mode: interactive loop in terminal with autonomous ReAct execution."""
    brain = Brain()
    memory = Memory()
    router = ToolRouter()  # Shared instance for stateful browser/session

    print("=" * 60)
    print("  JARVIS AI — Desktop Assistant (CLI)")
    print("  Type 'exit' or 'quit' to leave.")
    print("=" * 60)

    async def cli_callback(event_type: str, data: dict):
        """Stream ReAct events to terminal."""
        if event_type == "thinking":
            msg = data.get("message", "")
            print(f"\n  ⚙  {msg}")
        elif event_type == "tool_start":
            print(f"  ↳ [{data['tool']}] running...")
        elif event_type == "tool_result":
            status = "✔" if data.get("success") else "✘"
            print(f"  ↳ [{data['tool']}] {status}")

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye.")
            try:
                await router.cleanup()
            except Exception:
                pass
            break

        # ── Run with live spinner ─────────────────────────────
        spinner_active = [True]
        spinner_thread = threading.Thread(
            target=_spinner_task,
            args=(spinner_active, "JARVIS is thinking..."),
            daemon=True,
        )
        spinner_thread.start()

        try:
            result = await brain.execute_command(user_input, tool_router=router, callback=cli_callback)
        finally:
            spinner_active[0] = False
            spinner_thread.join()

        thought = result.get("summary", result.get("thought", ""))
        steps = result.get("steps", [])

        if not steps:
            # Chat mode — no tool calls
            print(f"JARVIS: {thought}")
            memory.save_task(user_input, [], thought, "chat")
            continue

        print(f"\nJARVIS: {thought}")

        output_lines = []
        for s in steps:
            status = "✔" if s["success"] else "✘"
            detail = s.get("output", s.get("error", ""))
            # Truncate very long output for readability
            detail_str = str(detail)
            if len(detail_str) > 500:
                detail_str = detail_str[:500] + "... (truncated)"
            output_lines.append(f"  {status} [{s['tool']}]: {detail_str}")

        print(f"\n  Steps ({len(steps)}):")
        print("\n".join(output_lines))

        memory.save_task(user_input, steps, thought, "done")


async def run_server():
    """Web dashboard mode: start FastAPI server."""
    from jarvis.web.server import create_app

    app = create_app()
    import uvicorn
    uvicorn.run(app, host=cfg.HOST, port=cfg.PORT, log_level="info")


if __name__ == "__main__":
    if "--cli" in sys.argv:
        asyncio.run(run_cli())
    else:
        import jarvis.config as cfg
        if not cfg.GEMINI_API_KEY:
            print("ERROR: GEMINI_API_KEY is not set. Set it in .env file.")
            sys.exit(1)
        print(f"Starting JARVIS web dashboard at http://{cfg.HOST}:{cfg.PORT}")
        asyncio.run(run_server())
