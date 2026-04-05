"""
YouTube Agent — Search, watch, comment, and browse channels.

Uses Chrome CDP to interact with youtube.com on the user's real session.
"""

import asyncio
import logging
from typing import Optional
from urllib.parse import quote_plus

from jarvis.tools.chrome_cdp import ChromeCDP, human_delay

logger = logging.getLogger(__name__)


class YouTubeAgent:
    """YouTube automation through CDP-connected Chrome."""

    BASE_URL = "https://www.youtube.com"

    def __init__(self):
        self._cdp: Optional[ChromeCDP] = None
        self._page = None

    async def _get_cdp(self) -> ChromeCDP:
        if self._cdp is None:
            self._cdp = await ChromeCDP.get_instance()
        return self._cdp

    async def open(self) -> dict:
        """Open or switch to YouTube tab."""
        try:
            cdp = await self._get_cdp()
            self._page = await cdp.find_or_open("youtube.com", self.BASE_URL)
            await asyncio.sleep(1)
            return {"success": True, "output": "YouTube ready", "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def search(self, query: str) -> dict:
        """Search YouTube for videos."""
        try:
            await self.open()

            # Use the search URL directly for reliability
            encoded = quote_plus(query)
            await self._page.goto(
                f"{self.BASE_URL}/results?search_query={encoded}",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            await asyncio.sleep(3)

            results = await self._page.evaluate(
                """() => {
                // Strategy 1: Standard video renderer
                let items = document.querySelectorAll('ytd-video-renderer, ytd-rich-item-renderer, ytd-compact-video-renderer');

                // Strategy 2: Fallback for different UI tests
                if (!items || items.length === 0) {
                    items = document.querySelectorAll('[class*="video-renderer"]');
                }

                if (!items || items.length === 0) {
                    // Ultra-broad fallback: find links that point to /watch
                    const mainObj = document.querySelector('ytd-search, [role="main"]');
                    if (mainObj) {
                        const links = mainObj.querySelectorAll('a[href*="/watch?v="]');
                        const seen = new Set();
                        return Array.from(links).map(a => {
                            const href = a.href.split('&')[0];
                            if (seen.has(href)) return null;
                            seen.add(href);
                            const container = a.closest('ytd-video-renderer, ytd-rich-item-renderer, div[id="dismissible"]') || a.parentElement;
                            const titleEl = container.querySelector('#video-title, #video-title-link, [title]') || a;
                            const title = titleEl.innerText.trim() || titleEl.getAttribute('title') || '';
                            if (!title) return null;
                            
                            return {
                                title: title,
                                channel: (container.querySelector('#channel-name a, .ytd-channel-name a, #text.ytd-channel-name') || {}).innerText || '',
                                views: (container.querySelector('#metadata-line span') || {}).innerText || '',
                                duration: (container.querySelector('.badge-shape-wiz__text, span.ytd-thumbnail-overlay-time-status-renderer') || {}).innerText || '',
                                url: href
                            };
                        }).filter(v => v && v.title);
                    }
                    return [];
                }

                return Array.from(items).slice(0, 15).map(v => ({
                    title: (v.querySelector('#video-title, #video-title-link') || {}).innerText || (v.querySelector('[title]') || {}).title || '',
                    channel: (v.querySelector('#channel-name a, .ytd-channel-name a, #text.ytd-channel-name, [class*="channel-name"]') || {}).innerText || '',
                    views: (v.querySelector('#metadata-line span') || {}).innerText || '',
                    duration: (v.querySelector('.badge-shape-wiz__text, span.ytd-thumbnail-overlay-time-status-renderer, [class*="time-status"]') || {}).innerText || '',
                    url: (v.querySelector('a#thumbnail, a#video-title-link, a[href*="watch"]') || {}).href || ''
                })).filter(v => v.title);
            }"""
            )
            return {
                "success": True,
                "output": {"results": results, "count": len(results)},
                "error": None,
            }
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def watch_video(self, url: str) -> dict:
        """Navigate to and play a YouTube video."""
        try:
            await self.open()
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Try to dismiss any ads or prompts
            try:
                skip_btn = await self._page.query_selector(
                    '.ytp-ad-skip-button, .ytp-ad-skip-button-modern, [class*="skip"]'
                )
                if skip_btn:
                    await skip_btn.click()
            except Exception:
                pass

            title = await self._page.evaluate(
                """() => (document.querySelector('h1.ytd-video-primary-info-renderer, yt-formatted-string.ytd-watch-metadata') || {}).innerText || ''"""
            )
            return {
                "success": True,
                "output": f"Playing: {title}",
                "error": None,
            }
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def post_comment(self, video_url: str, comment: str) -> dict:
        """Post a comment on a YouTube video."""
        try:
            await self.open()
            await self._page.goto(video_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Scroll down to load comments
            await self._page.evaluate("window.scrollBy(0, 600)")
            await asyncio.sleep(2)

            # Click the comment placeholder
            comment_box = await self._page.wait_for_selector(
                '#simplebox-placeholder, [placeholder*="comment"]',
                timeout=10000,
            )
            await comment_box.click()
            await asyncio.sleep(1)

            # Type in the editable area
            editor = await self._page.wait_for_selector(
                '#contenteditable-root, [contenteditable="true"]',
                timeout=5000,
            )
            await editor.type(comment, delay=30)
            await human_delay(0.5, 1.0)

            # Click submit
            submit_btn = await self._page.query_selector(
                '#submit-button, button[aria-label*="Comment"]'
            )
            if submit_btn:
                await submit_btn.click()
                await human_delay()
                return {
                    "success": True,
                    "output": f"Comment posted: {comment[:50]}...",
                    "error": None,
                }

            return {
                "success": False,
                "output": None,
                "error": "Submit button not found",
            }
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def get_channel_videos(self, channel_url: str) -> dict:
        """Get the latest videos from a YouTube channel."""
        try:
            await self.open()
            # Ensure we're on the /videos tab
            url = channel_url.rstrip("/")
            if not url.endswith("/videos"):
                url += "/videos"

            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            videos = await self._page.evaluate(
                """() => {
                return Array.from(
                    document.querySelectorAll('ytd-rich-item-renderer, ytd-grid-video-renderer')
                ).slice(0, 20).map(v => ({
                    title: (v.querySelector('#video-title, #video-title-link') || {}).innerText || '',
                    views: (v.querySelector('#metadata-line span') || {}).innerText || '',
                    published: (v.querySelector('#metadata-line span:nth-child(2)') || {}).innerText || '',
                    url: (v.querySelector('a#thumbnail, a#video-title-link, a[href*="watch"]') || {}).href || ''
                })).filter(v => v.title);
            }"""
            )
            return {
                "success": True,
                "output": {"videos": videos, "count": len(videos)},
                "error": None,
            }
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def get_video_info(self, url: str) -> dict:
        """Get detailed info about a specific video."""
        try:
            await self.open()
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            info = await self._page.evaluate(
                """() => ({
                title: (document.querySelector('h1.ytd-video-primary-info-renderer, yt-formatted-string.ytd-watch-metadata') || {}).innerText || '',
                channel: (document.querySelector('#channel-name a, ytd-channel-name a') || {}).innerText || '',
                views: (document.querySelector('.view-count, [data-info-type="views"]') || {}).innerText || '',
                likes: (document.querySelector('#segmented-like-button button[aria-label], [aria-label*="like"]') || {}).getAttribute('aria-label') || '',
                description: (document.querySelector('#description-inline-expander, #description') || {}).innerText || '',
                subscribers: (document.querySelector('#owner-sub-count') || {}).innerText || ''
            })"""
            )
            return {"success": True, "output": info, "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}
