"""
Chrome CDP — Connect Playwright to the user's real Chrome browser.

Provides tab management, page interaction, and human-like delay utilities.
All app agents (LinkedIn, Upwork, WhatsApp, etc.) share this single connection.

KEY DESIGN: Uses the user's REAL Chrome profile so all logins (WhatsApp,
Gmail, LinkedIn, etc.) are preserved. If Chrome is already running without
CDP, it will be closed and relaunched with the debug port.
"""

import asyncio
import logging
import os
import random
import subprocess
import time
from typing import Optional

import psutil

import jarvis.config as cfg

logger = logging.getLogger(__name__)


def _find_chrome_processes() -> list[dict]:
    """Find all running Chrome processes and check if they have CDP enabled."""
    results = []
    for proc in psutil.process_iter(["name", "cmdline", "pid"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if "chrome" not in name:
                continue
            cmdline = proc.info.get("cmdline") or []
            has_cdp = any(
                f"--remote-debugging-port=" in arg for arg in cmdline
            )
            results.append({
                "pid": proc.info["pid"],
                "name": name,
                "cmdline": cmdline,
                "has_cdp": has_cdp,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return results


def _chrome_running_with_cdp() -> bool:
    """Check if Chrome is already running with the CDP debug port."""
    procs = _find_chrome_processes()
    return any(p["has_cdp"] for p in procs)


def _chrome_running_without_cdp() -> bool:
    """Check if Chrome is running but WITHOUT CDP (normal user session)."""
    procs = _find_chrome_processes()
    return len(procs) > 0 and not any(p["has_cdp"] for p in procs)


def _get_default_chrome_profile() -> str:
    """Get the default Chrome user data directory on Windows."""
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        default = os.path.join(local_app_data, "Google", "Chrome", "User Data")
        if os.path.exists(default):
            return default
    return cfg.CHROME_PROFILE_DIR  # Fallback to config


def _kill_chrome():
    """Kill all Chrome processes so we can relaunch with CDP."""
    logger.info("Closing existing Chrome to relaunch with CDP...")
    try:
        # Graceful kill on Windows
        subprocess.run(
            ["taskkill", "/IM", "chrome.exe", "/F"],
            capture_output=True,
            timeout=10,
        )
        time.sleep(2)  # Wait for processes to fully exit
    except Exception as e:
        logger.warning(f"Failed to kill Chrome: {e}")


def launch_chrome_cdp():
    """
    Launch Chrome with --remote-debugging-port.

    Strategy:
    1. If Chrome is already running with CDP → do nothing, connect.
    2. If Chrome is running WITHOUT CDP → kill it, relaunch with CDP.
    3. If Chrome is not running → launch with CDP.

    Always uses the user's REAL Chrome profile so logins persist.
    """
    if _chrome_running_with_cdp():
        logger.info(f"Chrome already running with CDP on port {cfg.CDP_PORT}")
        return True

    # If Chrome is running without CDP, we need to restart it
    if _chrome_running_without_cdp():
        logger.warning(
            "Chrome is running WITHOUT CDP. Restarting with debug port..."
        )
        _kill_chrome()

    chrome_path = cfg.CHROME_PATH
    # Use the user's REAL Chrome profile (preserves all logins!)
    profile_dir = cfg.CHROME_PROFILE_DIR
    if profile_dir == r"C:\ChromeJarvisProfile":
        # User hasn't set a custom profile — use their real one
        profile_dir = _get_default_chrome_profile()
        logger.info(f"Using real Chrome profile: {profile_dir}")

    try:
        subprocess.Popen(
            [
                chrome_path,
                f"--remote-debugging-port={cfg.CDP_PORT}",
                f"--user-data-dir={profile_dir}",
                "--no-first-run",
                "--no-default-browser-check",
                "--start-maximized",
                "--restore-last-session",  # Reopen all previous tabs!
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Wait for Chrome to fully start and restore tabs
        time.sleep(5)
        logger.info(f"Chrome launched with CDP on port {cfg.CDP_PORT}")
        return True
    except FileNotFoundError:
        logger.error(f"Chrome not found at {chrome_path}. Update CHROME_PATH in .env")
        return False
    except Exception as e:
        logger.error(f"Failed to launch Chrome: {e}")
        return False


def _bring_chrome_foreground():
    """Bring Chrome window to foreground (un-minimize + focus) on Windows."""
    try:
        import pygetwindow as gw
        chrome_wins = gw.getWindowsWithTitle("Chrome")
        if chrome_wins:
            win = chrome_wins[0]
            if win.isMinimized:
                win.restore()
            win.activate()
            time.sleep(0.3)
            logger.debug("Chrome window brought to foreground")
            return True
    except Exception as e:
        # Fallback: use PowerShell to activate Chrome
        try:
            subprocess.run(
                [
                    "powershell", "-Command",
                    '(New-Object -ComObject WScript.Shell).AppActivate("Chrome")'
                ],
                capture_output=True,
                timeout=5,
            )
            return True
        except Exception:
            pass
        logger.debug(f"Could not bring Chrome to foreground: {e}")
    return False


async def human_delay(min_s: float = None, max_s: float = None):
    """Sleep for a random human-like duration (anti-detection)."""
    lo = min_s or cfg.RATE_LIMITS["min_delay_seconds"]
    hi = max_s or cfg.RATE_LIMITS["max_delay_seconds"]
    await asyncio.sleep(random.uniform(lo, hi))


class ChromeCDP:
    """
    Playwright CDP connection to the user's real Chrome.

    Usage:
        cdp = ChromeCDP()
        await cdp.connect()
        tabs = await cdp.get_all_tabs()
        page = await cdp.find_or_open("web.whatsapp.com", "https://web.whatsapp.com")
    """

    _instance: Optional["ChromeCDP"] = None

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._context = None
        self._connected = False

    @classmethod
    async def get_instance(cls) -> "ChromeCDP":
        """Singleton — all app agents share the same CDP connection."""
        if cls._instance is None or not cls._instance._connected:
            cls._instance = cls()
            await cls._instance.connect()
        return cls._instance

    async def connect(self):
        """Connect to Chrome via CDP."""
        if self._connected and self._browser and self._browser.is_connected():
            return

        # Ensure Chrome is running with CDP
        if not _chrome_running_with_cdp():
            launched = launch_chrome_cdp()
            if not launched:
                raise RuntimeError(
                    "Cannot launch Chrome with CDP. "
                    "Start Chrome manually with: "
                    f'chrome.exe --remote-debugging-port={cfg.CDP_PORT} '
                    f'--user-data-dir="{_get_default_chrome_profile()}"'
                )

        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()

        # Retry connection a few times (Chrome may need time to start)
        last_error = None
        for attempt in range(5):
            try:
                self._browser = await self._playwright.chromium.connect_over_cdp(
                    f"http://localhost:{cfg.CDP_PORT}"
                )
                self._context = self._browser.contexts[0]
                self._connected = True
                tab_count = len(self._context.pages)
                logger.info(
                    f"CDP connected to Chrome. {tab_count} tab(s) open."
                )

                # Log open tabs for debugging
                for i, page in enumerate(self._context.pages):
                    try:
                        title = await page.title()
                        logger.info(f"  Tab {i}: {title} ({page.url[:60]})")
                    except Exception:
                        logger.info(f"  Tab {i}: {page.url[:60]}")
                return
            except Exception as e:
                last_error = e
                logger.warning(
                    f"CDP connect attempt {attempt + 1}/5 failed: {e}"
                )
                await asyncio.sleep(2)

        raise RuntimeError(f"Failed to connect to Chrome CDP after 5 attempts: {last_error}")

    @property
    def context(self):
        return self._context

    @property
    def browser(self):
        return self._browser

    async def get_all_tabs(self) -> list[dict]:
        """List all open tabs with index, title, and URL."""
        tabs = []
        for i, page in enumerate(self._context.pages):
            try:
                title = await page.title()
            except Exception:
                title = "(loading...)"
            tabs.append({"index": i, "title": title, "url": page.url})
        return tabs

    async def switch_to_tab(
        self,
        index: int = None,
        url_contains: str = None,
        title_contains: str = None,
    ):
        """Switch to a tab by index, URL substring, or title substring."""
        for i, page in enumerate(self._context.pages):
            if index is not None and i == index:
                _bring_chrome_foreground()
                await page.bring_to_front()
                return page
            if url_contains and url_contains in page.url:
                _bring_chrome_foreground()
                await page.bring_to_front()
                return page
            if title_contains:
                try:
                    title = await page.title()
                    if title_contains.lower() in title.lower():
                        _bring_chrome_foreground()
                        await page.bring_to_front()
                        return page
                except Exception:
                    continue
        return None

    async def open_url(self, url: str):
        """Open a URL in a new tab and bring it to front."""
        _bring_chrome_foreground()
        page = await self._context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.bring_to_front()
        return page

    async def find_or_open(self, url_fragment: str, full_url: str):
        """
        Find an existing tab containing url_fragment.
        If not found, open full_url in a new tab.
        """
        page = await self.switch_to_tab(url_contains=url_fragment)
        if page:
            return page
        return await self.open_url(full_url)

    async def get_page_text(self, page) -> str:
        """Extract clean visible text from a page (strips nav/footer/scripts)."""
        return await page.evaluate(
            """() => {
            ['script','style','nav','footer','aside','header'].forEach(tag => {
                document.querySelectorAll(tag).forEach(el => el.remove())
            });
            return document.body.innerText;
        }"""
        )

    async def screenshot_tab(self, page, path: str = None) -> bytes:
        """Take a screenshot of a specific tab. Returns PNG bytes."""
        kwargs = {"type": "png"}
        if path:
            kwargs["path"] = path
        return await page.screenshot(**kwargs)

    async def close(self):
        """Disconnect from Chrome CDP (does NOT close Chrome)."""
        if self._browser:
            try:
                self._browser = None
                self._context = None
            except Exception:
                pass
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
        self._connected = False
        ChromeCDP._instance = None
        logger.info("CDP connection closed")
