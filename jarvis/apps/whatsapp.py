"""
WhatsApp Web — Automate messaging via the user's real Chrome session.

Uses Chrome CDP to interact with web.whatsapp.com.
Includes WhatsApp-specific keyboard shortcuts for reliability.
"""

import asyncio
import logging
from typing import Optional

from jarvis.tools.chrome_cdp import ChromeCDP, human_delay

logger = logging.getLogger(__name__)


class WhatsAppWeb:
    """WhatsApp Web automation through CDP-connected Chrome."""

    BASE_URL = "https://web.whatsapp.com"

    def __init__(self):
        self._cdp: Optional[ChromeCDP] = None
        self._page = None

    async def _get_cdp(self) -> ChromeCDP:
        if self._cdp is None:
            self._cdp = await ChromeCDP.get_instance()
        return self._cdp

    async def open(self) -> dict:
        """Open or switch to WhatsApp Web tab."""
        try:
            cdp = await self._get_cdp()
            self._page = await cdp.find_or_open("web.whatsapp.com", self.BASE_URL)

            # Wait for WhatsApp to fully load (search icon appears)
            try:
                await self._page.wait_for_selector(
                    '[data-icon="search"], [data-testid="chat-list-search"]',
                    timeout=15000,
                )
            except Exception:
                # May already be loaded or QR scan needed
                pass

            return {"success": True, "output": "WhatsApp Web ready", "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def _search_contact(self, name: str):
        """Search for a contact — uses keyboard shortcut + multiple selector fallbacks."""
        # Escape any open dialogs first
        await self._page.keyboard.press("Escape")
        await asyncio.sleep(0.5)

        # ── Method 1: Keyboard shortcut Ctrl+Alt+/ to focus search ──
        search_focused = False
        try:
            await self._page.keyboard.down("Control")
            await self._page.keyboard.down("Alt")
            await self._page.keyboard.press("/")
            await self._page.keyboard.up("Alt")
            await self._page.keyboard.up("Control")
            await asyncio.sleep(0.8)
            search_focused = True
        except Exception:
            pass

        # ── Method 2: Click the search bar directly ──
        if not search_focused:
            search_selectors = [
                '[data-testid="chat-list-search"]',
                '[data-icon="search"]',
                'div[role="textbox"][title="Search input textbox"]',
                'div[contenteditable="true"][data-tab="3"]',
            ]
            for sel in search_selectors:
                try:
                    el = await self._page.query_selector(sel)
                    if el:
                        await el.click()
                        await asyncio.sleep(0.5)
                        search_focused = True
                        break
                except Exception:
                    continue

        if not search_focused:
            logger.warning("WhatsApp: could not focus search bar")
            return False

        # ── Clear any existing text and type the contact name ──
        # Select all existing text first, then replace
        await self._page.keyboard.down("Control")
        await self._page.keyboard.press("a")
        await self._page.keyboard.up("Control")
        await asyncio.sleep(0.2)

        await self._page.keyboard.type(name, delay=60)
        await asyncio.sleep(2.5)  # WhatsApp needs time to filter contacts

        # ── Click the first search result ──
        result_selectors = [
            '[data-testid="cell-frame-container"]',
            '[data-testid="chat-list"] [role="listitem"]',
            'div[role="listitem"] span[title]',
            '#pane-side [role="listitem"]',
            '._amig',  # WhatsApp internal class for chat rows
        ]

        for sel in result_selectors:
            try:
                first_result = await self._page.query_selector(sel)
                if first_result:
                    await first_result.click()
                    await asyncio.sleep(0.8)
                    logger.info(f"WhatsApp: found contact '{name}' via selector '{sel}'")
                    return True
            except Exception:
                continue

        # ── Retry: try pressing Enter (sometimes selects the top result) ──
        try:
            await self._page.keyboard.press("Enter")
            await asyncio.sleep(1)
            # Check if a chat opened (message input box appears)
            msg_box = await self._page.query_selector(
                'div[contenteditable="true"][data-tab="10"], '
                'footer div[contenteditable="true"], '
                '[data-testid="conversation-compose-box-input"]'
            )
            if msg_box:
                logger.info(f"WhatsApp: found contact '{name}' via Enter key")
                return True
        except Exception:
            pass

        logger.warning(f"WhatsApp: contact '{name}' not found after all attempts")
        return False

    async def send_message(self, contact: str, message: str) -> dict:
        """Open a contact's chat and send a message."""
        try:
            await self.open()
            found = await self._search_contact(contact)
            if not found:
                return {
                    "success": False,
                    "output": None,
                    "error": f"Contact '{contact}' not found",
                }

            # Type in the message input box — try multiple selectors
            msg_box = None
            msg_selectors = [
                'div[contenteditable="true"][data-tab="10"]',
                '[data-testid="conversation-compose-box-input"]',
                'footer div[contenteditable="true"]',
                'div[contenteditable="true"][data-tab="6"]',
                '#main footer div[contenteditable="true"]',
            ]
            for sel in msg_selectors:
                try:
                    msg_box = await self._page.wait_for_selector(sel, timeout=3000)
                    if msg_box:
                        break
                except Exception:
                    continue

            if not msg_box:
                return {
                    "success": False,
                    "output": None,
                    "error": "Could not find message input box",
                }

            await msg_box.click()
            await msg_box.type(message, delay=30)
            await human_delay(0.3, 0.8)

            # Press Enter to send
            await self._page.keyboard.press("Enter")
            await human_delay(0.5, 1.0)

            logger.info(f"WhatsApp: sent message to {contact}")
            return {
                "success": True,
                "output": f"Message sent to {contact}: {message[:50]}...",
                "error": None,
            }
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def read_recent_messages(self, contact: str, count: int = 10) -> dict:
        """Read the last N messages from a contact's chat."""
        try:
            await self.open()
            found = await self._search_contact(contact)
            if not found:
                return {
                    "success": False,
                    "output": None,
                    "error": f"Contact '{contact}' not found",
                }

            # Wait for chat messages to fully render
            await asyncio.sleep(3)

            # Try multiple extraction strategies
            messages = await self._page.evaluate(
                """(count) => {
                // Strategy 1: data-testid based (newer WhatsApp)
                let msgs = document.querySelectorAll('[data-testid="msg-container"]');

                // Strategy 2: message row role
                if (!msgs || msgs.length === 0) {
                    msgs = document.querySelectorAll('div[role="row"] div.message-in, div[role="row"] div.message-out');
                }

                // Strategy 3: class-based (message-in / message-out)
                if (!msgs || msgs.length === 0) {
                    msgs = document.querySelectorAll('.message-in, .message-out');
                }

                // Strategy 4: conversation panel broad extraction
                if (!msgs || msgs.length === 0) {
                    const panel = document.querySelector('#main [role="application"], #main .copyable-area');
                    if (panel) {
                        msgs = panel.querySelectorAll('[data-pre-plain-text], [class*="message"]');
                    }
                }

                if (!msgs || msgs.length === 0) return [];

                const lastN = Array.from(msgs).slice(-count);
                return lastN.map(m => {
                    // Extract timestamp from data-pre-plain-text attr (format: "[HH:MM, M/D/YYYY] Name: ")
                    const preText = m.querySelector('[data-pre-plain-text]');
                    let time = '';
                    let sender = '';
                    if (preText) {
                        const attr = preText.getAttribute('data-pre-plain-text') || '';
                        const match = attr.match(/\\[([^\\]]+)\\]\\s*(.+?):/);
                        if (match) {
                            time = match[1].trim();
                            sender = match[2].trim();
                        }
                    }

                    // Get the actual message text (try copyable-text first, then innerText)
                    const copyable = m.querySelector('.copyable-text, [data-testid="balloon-text"], span.selectable-text');
                    let text = '';
                    if (copyable) {
                        text = copyable.innerText.trim();
                    } else {
                        // Fallback: get innerText but strip timestamps/metadata
                        text = m.innerText.trim();
                    }

                    // Determine direction
                    const isOutgoing = m.classList.contains('message-out') ||
                        m.closest('.message-out') !== null ||
                        m.closest('[data-testid="msg-container"]')?.classList?.contains('message-out');

                    return { text, time, sender, outgoing: !!isOutgoing };
                }).filter(m => m.text && m.text.length > 0);
            }""",
                count
            )

            if messages and len(messages) > 0:
                logger.info(f"WhatsApp: read {len(messages)} messages from {contact}")
            else:
                # Final fallback: extract ALL visible text from the conversation panel
                messages = await self._page.evaluate(
                    """(count) => {
                    const main = document.querySelector('#main');
                    if (!main) return [];

                    // Get all text nodes that look like messages
                    const spans = main.querySelectorAll('span.selectable-text span, span[dir="ltr"], span[dir="auto"]');
                    const seen = new Set();
                    const result = [];
                    for (const span of spans) {
                        const text = span.innerText.trim();
                        if (text && text.length > 0 && text.length < 5000 && !seen.has(text)) {
                            seen.add(text);
                            result.push({ text, time: '', sender: '', outgoing: false });
                        }
                    }
                    return result.slice(-count);
                }""",
                    count
                )
                logger.info(f"WhatsApp: read {len(messages)} messages (fallback) from {contact}")

            return {"success": True, "output": messages, "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def get_chat_list(self) -> dict:
        """Get a list of all visible chats in the sidebar."""
        try:
            await self.open()
            await asyncio.sleep(1)

            chats = await self._page.evaluate(
                """() => {
                // Strategy 1: data-testid selectors
                let items = document.querySelectorAll('[data-testid="cell-frame-title"]');
                if (items && items.length > 0) {
                    return Array.from(items).map(el => el.innerText);
                }

                // Strategy 2: listitem role with span[title]
                items = document.querySelectorAll('#pane-side [role="listitem"]');
                if (items && items.length > 0) {
                    return Array.from(items).map(item => {
                        const title = item.querySelector('span[title]');
                        return title ? title.getAttribute('title') : item.innerText.split('\\n')[0];
                    }).filter(t => t);
                }

                // Strategy 3: span[title] inside chat list
                items = document.querySelectorAll('#pane-side span[title]');
                if (items && items.length > 0) {
                    return Array.from(items)
                        .map(el => el.getAttribute('title'))
                        .filter(t => t && t.length < 100);
                }

                // Strategy 4: broad text extraction from side panel
                const pane = document.querySelector('#pane-side');
                if (pane) {
                    const rows = pane.querySelectorAll('[role="listitem"], [role="row"], [role="option"]');
                    if (rows.length > 0) {
                        return Array.from(rows).map(r => r.innerText.split('\\n')[0]).filter(t => t);
                    }
                    // Last resort: just get top-level text
                    return pane.innerText.split('\\n').filter(line =>
                        line.trim().length > 0 && line.trim().length < 100
                    ).slice(0, 30);
                }

                return [];
            }"""
            )
            logger.info(f"WhatsApp: found {len(chats)} chats")
            return {"success": True, "output": chats, "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def filter_unread(self) -> dict:
        """Show only unread chats using the Unread filter button."""
        try:
            await self.open()
            filter_btn = await self._page.query_selector(
                '[data-testid="filter-unread"], button[aria-label*="Unread"]'
            )
            if filter_btn:
                await filter_btn.click()
                await asyncio.sleep(1)

            chats = await self._page.evaluate(
                """() => {
                return Array.from(
                    document.querySelectorAll('[data-testid="cell-frame-container"]')
                ).map(c => c.innerText);
            }"""
            )
            return {"success": True, "output": chats, "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def send_file(self, contact: str, filepath: str) -> dict:
        """Send a file/document to a contact."""
        try:
            await self.open()
            found = await self._search_contact(contact)
            if not found:
                return {
                    "success": False,
                    "output": None,
                    "error": f"Contact '{contact}' not found",
                }

            # Click attachment icon
            attach_btn = await self._page.query_selector(
                '[data-testid="attach-menu-icon"], [data-icon="attach-menu-plus"]'
            )
            if attach_btn:
                await attach_btn.click()
                await asyncio.sleep(0.5)

                # Click Document option
                doc_btn = await self._page.query_selector(
                    '[data-testid="mi-attach-document"]'
                )
                if doc_btn:
                    await doc_btn.click()
                    await asyncio.sleep(1)

                    # Handle file input
                    file_input = await self._page.query_selector('input[type="file"]')
                    if file_input:
                        await file_input.set_input_files(filepath)
                        await asyncio.sleep(2)

                        # Click send on the file preview
                        send_btn = await self._page.query_selector(
                            '[data-testid="send"], [data-icon="send"]'
                        )
                        if send_btn:
                            await send_btn.click()
                            await human_delay()
                            return {
                                "success": True,
                                "output": f"File sent to {contact}: {filepath}",
                                "error": None,
                            }

            return {
                "success": False,
                "output": None,
                "error": "Could not find attachment controls",
            }
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}
