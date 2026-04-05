"""
Gmail Web — Automate email via the user's real Chrome session.

Uses Chrome CDP to interact with mail.google.com.
"""

import asyncio
import logging
from typing import Optional

from jarvis.tools.chrome_cdp import ChromeCDP, human_delay

logger = logging.getLogger(__name__)


class GmailWeb:
    """Gmail web automation through CDP-connected Chrome."""

    BASE_URL = "https://mail.google.com"

    def __init__(self):
        self._cdp: Optional[ChromeCDP] = None
        self._page = None

    async def _get_cdp(self) -> ChromeCDP:
        if self._cdp is None:
            self._cdp = await ChromeCDP.get_instance()
        return self._cdp

    async def open(self) -> dict:
        """Open or switch to Gmail tab."""
        try:
            cdp = await self._get_cdp()
            self._page = await cdp.find_or_open("mail.google.com", self.BASE_URL)

            # Wait for Gmail to fully load (Compose button)
            try:
                await self._page.wait_for_selector(
                    '[gh="cm"], [data-tooltip*="Compose"], .T-I-KE',
                    timeout=15000,
                )
            except Exception:
                pass  # May already be loaded

            return {"success": True, "output": "Gmail ready", "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def compose(self, to: str, subject: str, body: str) -> dict:
        """Compose and send an email."""
        try:
            await self.open()

            # Click Compose button
            compose_btn = await self._page.query_selector(
                '[gh="cm"], .T-I-KE, [data-tooltip*="Compose"]'
            )
            if compose_btn:
                await compose_btn.click()
            else:
                # Try keyboard shortcut
                await self._page.keyboard.press("c")
            await asyncio.sleep(1.5)

            # Fill "To" field
            to_field = await self._page.wait_for_selector(
                '[name="to"], [aria-label="To recipients"]',
                timeout=5000,
            )
            await to_field.type(to, delay=30)
            await self._page.keyboard.press("Tab")
            await asyncio.sleep(0.3)

            # Fill Subject
            subject_field = await self._page.query_selector(
                '[name="subjectbox"], [aria-label="Subject"]'
            )
            if subject_field:
                await subject_field.type(subject, delay=20)
            await asyncio.sleep(0.3)

            # Fill Body
            body_field = await self._page.query_selector(
                '[role="textbox"][aria-label*="Body"], '
                '[role="textbox"][aria-label*="Message Body"], '
                'div[aria-label*="Message Body"]'
            )
            if body_field:
                await body_field.click()
                await body_field.type(body, delay=15)
            await human_delay(0.5, 1.0)

            # Click Send (Ctrl+Enter or click button)
            send_btn = await self._page.query_selector(
                '[data-tooltip*="Send"], [aria-label*="Send"]'
            )
            if send_btn:
                await send_btn.click()
            else:
                await self._page.keyboard.down("Control")
                await self._page.keyboard.press("Enter")
                await self._page.keyboard.up("Control")

            await asyncio.sleep(1)
            logger.info(f"Gmail: sent email to {to}")
            return {
                "success": True,
                "output": f"Email sent to {to} — Subject: {subject}",
                "error": None,
            }
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def search_emails(self, query: str) -> dict:
        """Search emails using Gmail's search bar."""
        try:
            await self.open()

            # Click search box or use / shortcut
            search_box = await self._page.query_selector(
                '[name="q"], [aria-label="Search mail"]'
            )
            if search_box:
                await search_box.click()
                await search_box.fill("")
                await search_box.type(query, delay=30)
            else:
                await self._page.keyboard.press("/")
                await asyncio.sleep(0.5)
                await self._page.keyboard.type(query, delay=30)

            await self._page.keyboard.press("Enter")
            await asyncio.sleep(2)

            # Extract search results
            results = await self._page.evaluate(
                """() => {
                return Array.from(
                    document.querySelectorAll('tr.zA, tr[data-legacy-thread-id]')
                ).slice(0, 20).map(row => ({
                    from: (row.querySelector('.yP, .zF, [email]') || {}).innerText || '',
                    subject: (row.querySelector('.y6, .bog') || {}).innerText || '',
                    preview: (row.querySelector('.y2, .xT .y2') || {}).innerText || '',
                    time: (row.querySelector('.xW, .xW span') || {}).innerText || '',
                    unread: row.classList.contains('zE')
                }));
            }"""
            )
            return {"success": True, "output": results, "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def read_latest_emails(self, count: int = 5) -> dict:
        """Read the latest N emails from the inbox."""
        try:
            await self.open()

            # Navigate to inbox
            await self._page.goto(f"{self.BASE_URL}/mail/u/0/#inbox", wait_until="domcontentloaded")
            await asyncio.sleep(2)

            emails = await self._page.evaluate(
                f"""() => {{
                return Array.from(
                    document.querySelectorAll('tr.zA, tr[data-legacy-thread-id]')
                ).slice(0, {count}).map(row => ({{
                    from: (row.querySelector('.yP, .zF, [email]') || {{}}).innerText || '',
                    subject: (row.querySelector('.y6, .bog') || {{}}).innerText || '',
                    preview: (row.querySelector('.y2, .xT .y2') || {{}}).innerText || '',
                    time: (row.querySelector('.xW, .xW span') || {{}}).innerText || '',
                    unread: row.classList.contains('zE')
                }}));
            }}"""
            )
            return {"success": True, "output": emails, "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def open_email(self, index: int = 0) -> dict:
        """Open an email at the given index and read its full body."""
        try:
            await self.open()
            rows = await self._page.query_selector_all(
                "tr.zA, tr[data-legacy-thread-id]"
            )
            if index < len(rows):
                await rows[index].click()
                await asyncio.sleep(2)

                body = await self._page.evaluate(
                    """() => {
                    const el = document.querySelector(
                        '[data-message-id] .ii.gt div, .a3s.aiL div'
                    );
                    return el ? el.innerText : '(could not extract body)';
                }"""
                )
                subject = await self._page.evaluate(
                    """() => {
                    const el = document.querySelector('h2.hP, [data-thread-perm-id] h2');
                    return el ? el.innerText : '';
                }"""
                )
                return {
                    "success": True,
                    "output": {"subject": subject, "body": body[:5000]},
                    "error": None,
                }
            return {
                "success": False,
                "output": None,
                "error": f"No email at index {index}",
            }
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}
