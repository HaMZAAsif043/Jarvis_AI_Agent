import asyncio
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class Browser:
    """Browser automation via Playwright (primary) with Selenium fallback."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright = None
        self._pw_browser = None
        self._pw_context = None
        self._pw_page = None
        self._sel_browser = None
        self._engine: str = "none"

    async def _init_playwright(self):
        """Initialize Playwright browser."""
        if self._pw_browser and self._pw_browser.is_connected():
            return
        try:
            from playwright.async_api import async_playwright  # type: ignore

            self._playwright = await async_playwright().start()
            self._pw_browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
            self._pw_context = await self._pw_browser.new_context(
                viewport={"width": 1280, "height": 900},
            )
            self._engine = "playwright"
        except Exception:
            logger.warning("Playwright not available, will fall back to Selenium")
            self._engine = "selenium"

    def _init_selenium(self):
        """Initialize Selenium browser (fallback)."""
        if self._sel_browser:
            return
        try:
            from selenium import webdriver  # type: ignore
            from selenium.webdriver.chrome.options import Options  # type: ignore

            opts = Options()
            if self.headless:
                opts.add_argument("--headless")
            opts.add_argument("--disable-blink-features=AutomationControlled")
            self._sel_browser = webdriver.Chrome(options=opts)
            self._engine = "selenium"
        except Exception:
            self._engine = "none"
            raise RuntimeError("Neither Playwright nor Selenium is available")

    async def _get_browser(self):
        """Return active browser, initializing if needed."""
        if self._engine == "none":
            await self._init_playwright()
        if self._engine == "playwright":
            return "playwright", self._pw_browser
        else:
            self._init_selenium()
            return "selenium", self._sel_browser

    async def _get_page(self):
        """Get or create the current Playwright page."""
        if self._pw_page is None:
            if self._pw_context is None:
                await self._init_playwright()
                if self._engine != "playwright":
                    raise RuntimeError("Playwright context not available")
            self._pw_context = self._pw_context or await self._pw_browser.new_context()
            self._pw_page = await self._pw_context.new_page()
        return self._pw_page

    async def open_url(self, url: str) -> dict:
        """Open a URL in the browser and wait for it to load."""
        try:
            engine, browser = await self._get_browser()
            if engine == "playwright":
                page = await self._get_page()
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                title = await page.title()
                await page.wait_for_load_state("networkidle", timeout=10000)
                return {"success": True, "output": f"Opened {url} — title: {title}", "error": None}
            else:
                browser.get(url)
                return {"success": True, "output": f"Opened {url} — title: {browser.title}", "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def screenshot(self, output_path: str = "page_screenshot.png") -> dict:
        """Take a screenshot of the current page (not a default page)."""
        try:
            engine, browser = await self._get_browser()
            if engine == "playwright":
                page = await self._get_page()
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                await page.screenshot(path=output_path, full_page=True)
                return {"success": True, "output": f"Screenshot saved to {output_path}", "error": None}
            else:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                browser.save_screenshot(output_path)
                return {"success": True, "output": f"Screenshot saved to {output_path}", "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def get_page_text(self, url: Optional[str] = None) -> dict:
        """Open a URL (optional) and extract all visible text."""
        try:
            engine, browser = await self._get_browser()
            if engine == "playwright":
                page = await self._get_page()
                if url:
                    await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                text = await page.inner_text("body")
                return {"success": True, "output": text[:50000], "error": None}
            else:
                if url:
                    browser.get(url)
                text = browser.find_element("tag name", "body").text
                return {"success": True, "output": text[:50000], "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def click_element(self, url: Optional[str] = None, selector: str = "", index: int = 1) -> dict:
        """Open a URL (optional) and click an element by CSS selector."""
        try:
            engine, browser = await self._get_browser()
            if engine == "playwright":
                page = await self._get_page()
                if url:
                    await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                # Click by text content if selector looks like text
                if selector.startswith("text=") or selector.startswith('"'):
                    await page.get_by_text(selector.strip('"').replace("text=", ""), exact=False).first.click()
                else:
                    await page.click(selector, timeout=10000)
                await page.wait_for_load_state("networkidle", timeout=10000)
                title = await page.title()
                return {"success": True, "output": f"Clicked '{selector}' — title: {title}", "error": None}
            else:
                from selenium.webdriver.common.by import By  # type: ignore
                if url:
                    browser.get(url)
                elem = browser.find_element(By.CSS_SELECTOR, selector)
                elem.click()
                return {"success": True, "output": f"Clicked '{selector}' — title: {browser.title}", "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def fill_form(self, url: Optional[str] = None, selector: str = "", value: str = "") -> dict:
        """Open a URL (optional) and fill a form field."""
        try:
            engine, browser = await self._get_browser()
            if engine == "playwright":
                page = await self._get_page()
                if url:
                    await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                await page.fill(selector, value, timeout=10000)
                return {"success": True, "output": f"Filled '{selector}' with value", "error": None}
            else:
                from selenium.webdriver.common.by import By  # type: ignore
                if url:
                    browser.get(url)
                elem = browser.find_element(By.CSS_SELECTOR, selector)
                elem.clear()
                elem.send_keys(value)
                return {"success": True, "output": f"Filled '{selector}' with value", "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def submit_form(self, url: Optional[str] = None, button_selector: str = "") -> dict:
        """Open a URL (optional) and click a submit button."""
        selector = button_selector or "input[type='submit'], button[type='submit']"
        return await self.click_element(url=url, selector=selector)

    async def get_element_text(self, url: Optional[str] = None, selector: str = "") -> dict:
        """Open a URL (optional) and extract text from a specific element."""
        try:
            engine, browser = await self._get_browser()
            if engine == "playwright":
                page = await self._get_page()
                if url:
                    await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                text = await page.inner_text(selector)
                return {"success": True, "output": text, "error": None}
            else:
                from selenium.webdriver.common.by import By  # type: ignore
                if url:
                    browser.get(url)
                elem = browser.find_element(By.CSS_SELECTOR, selector)
                return {"success": True, "output": elem.text, "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def get_html(self, url: Optional[str] = None) -> dict:
        """Open a URL (optional) and get page HTML (truncated to 20KB)."""
        try:
            engine, browser = await self._get_browser()
            if engine == "playwright":
                page = await self._get_page()
                if url:
                    await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                html = await page.content()
                return {"success": True, "output": html[:20000], "error": None}
            else:
                if url:
                    browser.get(url)
                return {"success": True, "output": browser.page_source[:20000], "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def wait(self, seconds: float = 2.0) -> dict:
        """Wait for N seconds in the browser."""
        try:
            await asyncio.sleep(seconds)
            return {"success": True, "output": f"Waited {seconds} seconds", "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def go_back(self) -> dict:
        """Go back in browser history."""
        try:
            engine, browser = await self._get_browser()
            if engine == "playwright":
                page = await self._get_page()
                await page.go_back()
                title = await page.title()
                return {"success": True, "output": f"Went back — title: {title}", "error": None}
            else:
                browser.back()
                return {"success": True, "output": f"Went back — title: {browser.title}", "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def get_page_title(self, url: Optional[str] = None) -> dict:
        """Get the current page title (optionally navigate first)."""
        try:
            engine, browser = await self._get_browser()
            if engine == "playwright":
                page = await self._get_page()
                if url:
                    await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                title = await page.title()
                return {"success": True, "output": title, "error": None}
            else:
                if url:
                    browser.get(url)
                return {"success": True, "output": browser.title, "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def select_option(self, url: Optional[str] = None, selector: str = "", value: str = "") -> dict:
        """Select a dropdown option by value."""
        try:
            engine, browser = await self._get_browser()
            if engine == "playwright":
                page = await self._get_page()
                if url:
                    await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                await page.select_option(selector, value=value)
                return {"success": True, "output": f"Selected '{value}' in '{selector}'", "error": None}
            else:
                from selenium.webdriver.common.by import By  # type: ignore
                from selenium.webdriver.support.ui import Select  # type: ignore
                if url:
                    browser.get(url)
                elem = browser.find_element(By.CSS_SELECTOR, selector)
                Select(elem).select_by_value(value)
                return {"success": True, "output": f"Selected '{value}' in '{selector}'", "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def close(self):
        """Clean up browser resources."""
        if self._pw_browser:
            try:
                await self._pw_browser.close()
            except Exception:
                pass
            self._pw_browser = None
            self._pw_context = None
            self._pw_page = None
        if self._sel_browser:
            try:
                self._sel_browser.quit()
            except Exception:
                pass
            self._sel_browser = None
        self._engine = "none"
