import asyncio
import json
import logging
import sys

import jarvis.config as cfg
from jarvis.agent.brain import Brain
from jarvis.agent.router import ToolRouter
from jarvis.agent.memory import Memory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def run_cli():
    """CLI mode: interactive loop in terminal with autonomous ReAct execution."""
    brain = Brain()
    memory = Memory()
    router = ToolRouter()  # Shared instance for stateful browser/session

    print("=" * 60)
    print("  JARVIS AI — Desktop Assistant (CLI)")
    print("  Type 'exit' or 'quit' to leave.")
    print("=" * 60)

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
            break

        result = await brain.execute_command(user_input, tool_router=router)

        thought = result.get("summary", result.get("thought", ""))
        steps = result.get("steps", [])

        if not steps:
            # Chat mode — no tool calls
            print(f"JARVIS: {thought}")
            memory.save_task(user_input, [], thought, "chat")
            continue

        print(f"JARVIS: {thought}")

        output_lines = []
        for s in steps:
            status = "OK" if s["success"] else "ERROR"
            detail = s.get("output", s.get("error", ""))
            output_lines.append(f"  [{s['tool']}] {status}: {str(detail)}")

        print(f"\nResults ({len(steps)} step(s)):")
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
