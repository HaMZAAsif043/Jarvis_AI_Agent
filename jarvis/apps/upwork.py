"""
Upwork Agent — Job search, proposal submission, messages, and contracts.

Uses Chrome CDP to interact with upwork.com on the user's real session.
Includes daily rate limiting for proposals.
"""

import asyncio
import logging
from datetime import date
from typing import Optional
from urllib.parse import quote_plus

import jarvis.config as cfg
from jarvis.tools.chrome_cdp import ChromeCDP, human_delay

logger = logging.getLogger(__name__)


class UpworkAgent:
    """Upwork automation for job hunting and client management."""

    BASE_URL = "https://www.upwork.com"

    def __init__(self):
        self._cdp: Optional[ChromeCDP] = None
        self._page = None
        self._daily_proposals = 0
        self._last_reset_date = date.today()

    def _check_reset_daily(self):
        today = date.today()
        if today != self._last_reset_date:
            self._daily_proposals = 0
            self._last_reset_date = today

    async def _get_cdp(self) -> ChromeCDP:
        if self._cdp is None:
            self._cdp = await ChromeCDP.get_instance()
        return self._cdp

    async def open(self) -> dict:
        """Open or switch to Upwork tab."""
        try:
            cdp = await self._get_cdp()
            self._page = await cdp.find_or_open("upwork.com", self.BASE_URL)
            await asyncio.sleep(1)
            return {"success": True, "output": "Upwork ready", "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def search_jobs(self, query: str, filters: dict = None) -> dict:
        """
        Search for jobs on Upwork.
        filters = {
            "min_budget": 500,
            "experience": "entry",   # entry / intermediate / expert
            "job_type": "fixed"      # fixed / hourly
        }
        """
        try:
            filters = filters or {}
            await self.open()

            encoded = quote_plus(query)
            url = f"{self.BASE_URL}/nx/search/jobs/?q={encoded}"

            # Apply filters
            if filters.get("job_type") == "fixed":
                url += "&payment_verified=1&budget=-&t=0"
            elif filters.get("job_type") == "hourly":
                url += "&payment_verified=1&t=1"

            exp_map = {"entry": "1", "intermediate": "2", "expert": "3"}
            if filters.get("experience") in exp_map:
                url += f"&contractor_tier={exp_map[filters['experience']]}"

            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            jobs = await self._page.evaluate(
                """() => {
                return Array.from(
                    document.querySelectorAll('[data-test="job-tile"], [data-ev-label="search_results_impression"], article')
                ).slice(0, 20).map(job => {
                    const titleEl = job.querySelector('h2 a, h3 a, [data-test="job-tile-title-link"]');
                    return {
                        title: titleEl ? titleEl.innerText.trim() : '',
                        budget: (job.querySelector('[data-test="budget"], [data-test="is-fixed-price"], .amount') || {}).innerText || '',
                        description: (job.querySelector('[data-test="UpCLineClamp JobDescription"] p, [data-test="description"], .air3-line-clamp') || {}).innerText || '',
                        skills: Array.from(
                            job.querySelectorAll('[data-test="attr-item"], [data-test="token"], .air3-token')
                        ).map(s => s.innerText.trim()),
                        posted: (job.querySelector('[data-test="posted-on"], [data-test="job-pubilshed-date"], small') || {}).innerText || '',
                        link: titleEl ? titleEl.href : ''
                    };
                }).filter(j => j.title);
            }"""
            )

            # Filter by min_budget if specified
            min_b = filters.get("min_budget")
            if min_b:
                filtered = []
                for j in jobs:
                    try:
                        budget_str = j.get("budget", "").replace("$", "").replace(",", "").strip()
                        # Handle ranges like "$500 - $1,000"
                        parts = budget_str.split("-")
                        high = float(parts[-1].strip()) if parts else 0
                        if high >= min_b:
                            filtered.append(j)
                    except (ValueError, IndexError):
                        filtered.append(j)  # Include if can't parse
                jobs = filtered

            return {
                "success": True,
                "output": {"jobs": jobs, "count": len(jobs)},
                "error": None,
            }
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def send_proposal(
        self,
        job_url: str,
        cover_letter: str,
        bid_amount: float,
        bid_type: str = "fixed",
    ) -> dict:
        """Submit a proposal to an Upwork job."""
        try:
            self._check_reset_daily()
            limit = cfg.RATE_LIMITS["upwork_proposals_per_day"]
            if self._daily_proposals >= limit:
                return {
                    "success": False,
                    "output": None,
                    "error": f"Daily proposal limit reached ({limit}). Try again tomorrow.",
                }

            await self.open()
            await self._page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Click "Apply Now" button
            apply_btn = await self._page.query_selector(
                '[data-test="apply-button"], button:has-text("Apply Now"), '
                'a[data-test="apply-button"]'
            )
            if not apply_btn:
                return {
                    "success": False,
                    "output": None,
                    "error": "Apply button not found.",
                }

            await apply_btn.click()
            await asyncio.sleep(3)

            # Set bid amount
            if bid_type == "hourly":
                rate_input = await self._page.query_selector(
                    '[data-test="rate-input"], input[aria-label*="hourly"]'
                )
                if rate_input:
                    await rate_input.fill("")
                    await rate_input.fill(str(bid_amount))
            else:
                bid_input = await self._page.query_selector(
                    '[data-test="fixed-price-input"], '
                    'input[aria-label*="bid"], '
                    'input[aria-label*="amount"]'
                )
                if bid_input:
                    await bid_input.fill("")
                    await bid_input.fill(str(bid_amount))
            await asyncio.sleep(1)

            # Write cover letter
            cover_input = await self._page.query_selector(
                '[data-test="cover-letter"] textarea, '
                'textarea[aria-label*="cover letter"], '
                'textarea[placeholder*="cover letter"], '
                '#cover-letter-area'
            )
            if cover_input:
                await cover_input.fill(cover_letter)
            await human_delay(1.0, 2.0)

            # Submit proposal
            submit_btn = await self._page.query_selector(
                '[data-test="submit-proposal"], '
                'button:has-text("Submit"), '
                'button[type="submit"]'
            )
            if submit_btn:
                await submit_btn.click()
                self._daily_proposals += 1
                await human_delay()
                return {
                    "success": True,
                    "output": f"✅ Proposal submitted! Bid: ${bid_amount} ({self._daily_proposals}/{limit} today)",
                    "error": None,
                }

            return {
                "success": False,
                "output": None,
                "error": "Submit button not found.",
            }
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def check_messages(self) -> dict:
        """Read all Upwork message threads."""
        try:
            await self.open()
            await self._page.goto(
                f"{self.BASE_URL}/messages/",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            await asyncio.sleep(3)

            threads = await self._page.evaluate(
                """() => {
                return Array.from(
                    document.querySelectorAll('[data-test="thread"], [data-qa="thread-item"], .thread-list-item')
                ).slice(0, 20).map(t => ({
                    contact: (t.querySelector('[data-test="thread-name"], .thread-title') || {}).innerText || '',
                    preview: (t.querySelector('[data-test="thread-preview"], .thread-message') || {}).innerText || '',
                    time: (t.querySelector('[data-test="thread-time"], .thread-time') || {}).innerText || '',
                    unread: t.classList.contains('unread') || !!t.querySelector('.unread-indicator')
                }));
            }"""
            )
            return {"success": True, "output": threads, "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def get_active_contracts(self) -> dict:
        """List all active Upwork contracts."""
        try:
            await self.open()
            await self._page.goto(
                f"{self.BASE_URL}/ab/contracts/",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            await asyncio.sleep(3)

            contracts = await self._page.evaluate(
                """() => {
                return Array.from(
                    document.querySelectorAll('[data-test="contract-card"], .contract-tile, tr[data-qa]')
                ).map(c => ({
                    client: (c.querySelector('[data-test="client-name"], .client-name') || {}).innerText || '',
                    title: (c.querySelector('[data-test="contract-title"], .contract-title') || {}).innerText || '',
                    rate: (c.querySelector('[data-test="rate"], .rate') || {}).innerText || '',
                    status: (c.querySelector('[data-test="status"], .contract-status') || {}).innerText || ''
                }));
            }"""
            )
            return {"success": True, "output": contracts, "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}
