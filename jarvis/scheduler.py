import logging
from typing import Callable, Awaitable
import jarvis.config as cfg
from jarvis.agent.brain import Brain
from jarvis.agent.router import ToolRouter
from jarvis.agent.memory import Memory

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
except ImportError:
    AsyncIOScheduler = None  # type: ignore
    CronTrigger = None  # type: ignore

logger = logging.getLogger(__name__)


class SchedulerManager:
    """Manages scheduled tasks using APScheduler."""

    def __init__(self, execute_fn: Callable[[str], Awaitable[str]]):
        self.execute_fn = execute_fn

        if AsyncIOScheduler is None:
            logger.warning("APScheduler not installed. Scheduled tasks disabled.")
            self._scheduler = None
            return

        self._scheduler = AsyncIOScheduler()
        # Load default tasks from config
        for task in cfg.SCHEDULER_TASKS:
            if CronTrigger is None:
                break
            name = task.get("name", "unnamed")
            cron = task.get("cron", "0 0 * * *")
            action = task.get("action", "")

            # Parse cron (5-field: minute hour day month weekday)
            parts = cron.split()
            self._scheduler.add_job(
                self._run_task,
                CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4],
                ),
                args=[action],
                name=name,
                replace_existing=True,
            )
            logger.info(f"Scheduled task: {name} ({cron})")

    async def _run_task(self, action: str):
        """Execute a scheduled task."""
        logger.info(f"Running scheduled task: {action}")
        try:
            result = await self.execute_fn(action)
            logger.info(f"Scheduled task result: {result}")
        except Exception as e:
            logger.error(f"Scheduled task failed: {e}")

    def schedule_task(self, name: str, cron: str, action: str):
        """Add a new scheduled task at runtime."""
        if self._scheduler is None:
            return {"error": "Scheduler not available"}

        if CronTrigger is None:
            return {"error": "CronTrigger not available"}

        parts = cron.split()
        if len(parts) != 5:
            return {"error": "Invalid cron format. Use: minute hour day month weekday"}

        self._scheduler.add_job(
            self._run_task,
            CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4],
            ),
            args=[action],
            name=name,
            replace_existing=True,
        )
        return {"success": True, "message": f"Task '{name}' scheduled: {cron}"}

    def list_tasks(self) -> list[dict]:
        """List all scheduled tasks."""
        if self._scheduler is None:
            return []
        jobs = self._scheduler.get_jobs()
        return [{"name": j.name, "trigger": str(j.trigger), "next_run": str(j.next_run_time)} for j in jobs]

    def start(self):
        """Start the scheduler."""
        if self._scheduler:
            self._scheduler.start()
            logger.info("Scheduler started")

    def stop(self):
        """Stop the scheduler."""
        if self._scheduler:
            self._scheduler.shutdown()
            logger.info("Scheduler stopped")
