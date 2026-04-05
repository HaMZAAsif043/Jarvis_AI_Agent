import os
import shutil
from pathlib import Path
from typing import Optional


class FileManager:
    """File and directory operations."""

    def read_file(self, path: str) -> dict:
        """Read file contents."""
        try:
            p = Path(path).expanduser()
            if not p.exists():
                return self._err(f"File not found: {p}")
            if p.is_dir():
                return self._err(f"Path is a directory: {p}")
            try:
                text = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = "(binary file)"
            return self._ok(output={"path": str(p), "content": text})
        except Exception as e:
            return self._err(str(e))

    def write_file(self, path: str, content: str) -> dict:
        """Write content to file (creates parent dirs if needed)."""
        try:
            p = Path(path).expanduser()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return self._ok(output=f"Written {len(content)} chars to {p}")
        except Exception as e:
            return self._err(str(e))

    def copy_file(self, source: str, destination: str) -> dict:
        """Copy file or directory."""
        try:
            src = Path(source).expanduser()
            dst = Path(destination).expanduser()
            if not src.exists():
                return self._err(f"Source not found: {src}")
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            return self._ok(output=f"Copied {src} -> {dst}")
        except Exception as e:
            return self._err(str(e))

    def move_file(self, source: str, destination: str) -> dict:
        """Move file or directory."""
        try:
            src = Path(source).expanduser()
            dst = Path(destination).expanduser()
            if not src.exists():
                return self._err(f"Source not found: {src}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            return self._ok(output=f"Moved {src} -> {dst}")
        except Exception as e:
            return self._err(str(e))

    def delete_file(self, path: str) -> dict:
        """Delete file or directory."""
        try:
            p = Path(path).expanduser()
            if not p.exists():
                return self._err(f"Not found: {p}")
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            return self._ok(output=f"Deleted {p}")
        except Exception as e:
            return self._err(str(e))

    def list_dir(self, path: str = ".") -> dict:
        """List directory contents."""
        try:
            p = Path(path).expanduser()
            if not p.is_dir():
                return self._err(f"Not a directory: {p}")
            entries = sorted(os.listdir(p))
            return self._ok(output={"path": str(p), "entries": entries})
        except Exception as e:
            return self._err(str(e))

    def search_files(self, path: str, pattern: str) -> dict:
        """Search for files by name pattern (glob)."""
        try:
            p = Path(path).expanduser()
            if not p.exists():
                p = Path(path)
            matches = [str(f) for f in p.rglob(pattern)]
            return self._ok(output={"pattern": pattern, "matches": matches, "count": len(matches)})
        except Exception as e:
            return self._err(str(e))

    def _ok(self, output) -> dict:
        return {"success": True, "output": output, "error": None}

    def _err(self, message: str) -> dict:
        return {"success": False, "output": None, "error": message}
