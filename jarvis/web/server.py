import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse

import jarvis.config as cfg
from jarvis.agent.brain import Brain
from jarvis.agent.router import ToolRouter
from jarvis.agent.memory import Memory
from jarvis.scheduler import SchedulerManager

logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).parent


class Connection:
    """Represents a single WS client with streaming callback."""

    def __init__(self, ws: WebSocket):
        self.ws = ws

    async def emit(self, event_type: str, data: dict):
        await self.ws.send_text(json.dumps({"type": event_type, "data": data}))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: start/stop scheduler."""
    app.state.scheduler.start()
    logger.info("JARVIS server started")
    yield
    app.state.scheduler.stop()


def create_app() -> FastAPI:
    app = FastAPI(title="JARVIS AI", lifespan=lifespan)

    brain = Brain()
    memory = Memory()
    router = ToolRouter()  # Shared instance for stateful browser/session

    async def execute_task(action_text: str, conn: Connection | None = None) -> str:
        """Execute a user action through Gemini -> autonomous ReAct loop."""
        if conn:
            await conn.emit("thinking", {"message": "Analyzing your request..."})

        async def stream_callback(event_type: str, data: dict):
            """Stream events to the WebSocket client."""
            if conn:
                await conn.emit(event_type, data)

        result = await brain.execute_command(action_text, tool_router=router, callback=stream_callback)

        summary = result.get("summary", result.get("thought", ""))
        steps = result.get("steps", [])
        success = result.get("success", True)

        # Emit final result
        if conn:
            await conn.emit("done", {
                "text": summary,
                "type": "action" if steps else "chat",
                "success": success,
                "steps_count": len(steps),
            })

        memory.save_task(
            action_text,
            [s for s in steps if s.get("success")],
            summary,
            "done" if success else "partial",
        )
        return summary

    async def schedule_execute_fn(action_text: str) -> str:
        """Wrapper for scheduler to execute tasks (no WebSocket)."""
        return await execute_task(action_text, conn=None)

    scheduler = SchedulerManager(execute_fn=schedule_execute_fn)
    app.state.scheduler = scheduler

    # --- Routes ---

    @app.get("/", response_class=HTMLResponse)
    async def index():
        html_file = WEB_DIR / "index.html"
        if not html_file.exists():
            return HTMLResponse("<h1>JARVIS dashboard not found.</h1>", 404)
        return HTMLResponse(html_file.read_text(encoding="utf-8"))

    @app.get("/api/tasks")
    async def get_tasks():
        return memory.get_history(limit=50)

    @app.get("/api/tools")
    async def get_tools():
        return {"tools": cfg.TOOLS}

    @app.get("/api/scheduler/tasks")
    async def get_scheduled_tasks():
        return scheduler.list_tasks()

    @app.post("/api/scheduler/add")
    async def add_scheduled_task(request: dict):
        name = request.get("name", "unnamed")
        cron = request.get("cron", "0 0 * * *")
        action = request.get("action", "")
        return scheduler.schedule_task(name, cron, action)

    @app.post("/api/command")
    async def post_command(request: dict):
        """REST fallback for executing commands (no real-time streaming)."""
        action = request.get("action", "")
        if not action:
            return {"error": "Missing 'action' field"}
        result = await execute_task(action, conn=None)
        return {"result": result}

    @app.websocket("/ws/execute")
    async def ws_execute(ws: WebSocket):
        """WebSocket endpoint: stream command execution in real-time."""
        await ws.accept()
        conn = Connection(ws)

        try:
            while True:
                data = await ws.receive_text()
                payload = json.loads(data)
                action = payload.get("action", "")

                if not action:
                    await conn.emit("error", {"message": "No action provided"})
                    continue

                if action.lower() in ("exit", "quit", "ping"):
                    await conn.emit("pong", {"message": "JARVIS is alive"})
                    continue

                # Handle schedule commands
                if action.startswith("schedule "):
                    try:
                        parts = action.split(" ", 2)[1].split("|", 2)
                        if len(parts) == 3:
                            result = scheduler.schedule_task(parts[0], parts[1], parts[2])
                            await conn.emit("done", {"text": f"Scheduled: {result}"})
                        else:
                            await conn.emit("error", {"message": "Usage: schedule name|cron|action"})
                    except Exception:
                        await conn.emit("error", {"message": "Invalid schedule command"})
                    continue

                # Execute through the pipeline
                await execute_task(action, conn=conn)

        except WebSocketDisconnect:
            logger.info("Client disconnected")
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
            try:
                await conn.emit("error", {"message": str(e)})
            except Exception:
                pass

    return app
