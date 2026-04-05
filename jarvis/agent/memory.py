import sqlite3
from pathlib import Path
from typing import Optional
import jarvis.config as cfg


class Memory:
    """SQLite-backed task history and conversation memory."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(cfg.MEMORY_DB)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_input TEXT NOT NULL,
                    tool_calls TEXT,
                    result TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at)")

    def save_task(self, user_input: str, tool_calls: list, result: str, status: str = "done") -> int:
        import json
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO tasks (user_input, tool_calls, result, status) VALUES (?, ?, ?, ?)",
                (user_input, json.dumps(tool_calls), result, status),
            )
            return cur.lastrowid

    def get_history(self, limit: int = 50) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, user_input, tool_calls, result, status, created_at FROM tasks ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def search_memory(self, query: str) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, user_input, tool_calls, result, status, created_at FROM tasks WHERE user_input LIKE ? ORDER BY created_at DESC LIMIT 20",
                (f"%{query}%",),
            ).fetchall()
            return [dict(r) for r in rows]
