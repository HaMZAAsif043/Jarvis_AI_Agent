"""
LinkedIn Agent — Lead generation, profile visits, connections, and job applications.

Uses Chrome CDP to interact with linkedin.com on the user's real session.
Includes daily rate limiting and human-like delays for anti-detection.
"""

import asyncio
import logging
from datetime import date
from typing import Optional
from urllib.parse import quote_plus

import jarvis.config as cfg
from jarvis.tools.chrome_cdp import ChromeCDP, human_delay

logger = logging.getLogger(__name__)


class LinkedInAgent:
    """LinkedIn automation for lead gen and job hunting."""

    BASE_URL = "https://www.linkedin.com"

    def __init__(self):
        self._cdp: Optional[ChromeCDP] = None
        self._page = None
        # Daily rate tracking
        self._daily_connections = 0
        self._daily_applications = 0
        self._last_reset_date = date.today()

    def _check_reset_daily(self):
        """Reset daily counters at midnight."""
        today = date.today()
        if today != self._last_reset_date:
            self._daily_connections = 0
            self._daily_applications = 0
            self._last_reset_date = today

    async def _get_cdp(self) -> ChromeCDP:
        if self._cdp is None:
            self._cdp = await ChromeCDP.get_instance()
        return self._cdp

    async def open(self) -> dict:
        """Open or switch to LinkedIn tab."""
        try:
            cdp = await self._get_cdp()
            self._page = await cdp.find_or_open("linkedin.com", self.BASE_URL)
            await asyncio.sleep(1)
            return {"success": True, "output": "LinkedIn ready", "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    # ── LEAD GENERATION ──────────────────────────────────────────

    async def search_leads(self, query: str, location: str = "") -> dict:
        """
        Search for people on LinkedIn.
        query = "CEO dental clinic New York"
        """
        try:
            await self.open()
            encoded = quote_plus(query)
            url = f"{self.BASE_URL}/search/results/people/?keywords={encoded}"
            if location:
                url += f"&geoUrn=%5B%22{quote_plus(location)}%22%5D"

            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # LinkedIn lazy-loads results — wait for them + scroll to trigger render
            await asyncio.sleep(4)
            await self._page.evaluate("window.scrollBy(0, 500)")
            await asyncio.sleep(2)

            leads = await self._page.evaluate(
                """() => {
                // Strategy 1: Modern LinkedIn (reusable-search)
                let cards = document.querySelectorAll('.reusable-search__result-container');

                // Strategy 2: entity-result template
                if (!cards || cards.length === 0) {
                    cards = document.querySelectorAll('[data-view-name="search-entity-result-universal-template"]');
                }

                // Strategy 3: li items in search results
                if (!cards || cards.length === 0) {
                    cards = document.querySelectorAll('.search-results-container li.reusable-search__result-container');
                }

                // Strategy 4: any list items with links to /in/ profiles
                if (!cards || cards.length === 0) {
                    cards = document.querySelectorAll('ul.reusable-search__entity-result-list > li');
                }

                // Strategy 5: broadest — any div containing a profile link
                if (!cards || cards.length === 0) {
                    cards = document.querySelectorAll('div[data-chameleon-result-urn], div[data-view-name]');
                }

                if (!cards || cards.length === 0) {
                    // Final fallback: extract from page text
                    const main = document.querySelector('main, [role="main"], .search-results-container');
                    if (main) {
                        // Look for all profile links
                        const links = main.querySelectorAll('a[href*="/in/"]');
                        const seen = new Set();
                        return Array.from(links).map(a => {
                            const href = a.href.split('?')[0];
                            if (seen.has(href)) return null;
                            seen.add(href);
                            // Walk up to find the containing card
                            const container = a.closest('li, div[class*="result"]') || a.parentElement;
                            const nameEl = container.querySelector('span[aria-hidden="true"]') || a;
                            return {
                                name: nameEl.innerText.trim(),
                                title: (container.querySelector('.entity-result__primary-subtitle, [class*="subtitle"]') || {}).innerText || '',
                                location: (container.querySelector('.entity-result__secondary-subtitle, [class*="secondary"]') || {}).innerText || '',
                                profileUrl: href
                            };
                        }).filter(l => l && l.name && l.name.length < 100);
                    }
                    return [];
                }

                return Array.from(cards).map(card => {
                    // Try multiple selectors for each field
                    const nameEl = card.querySelector(
                        'span[aria-hidden="true"], .entity-result__title-text a span, a[href*="/in/"] span'
                    );
                    const titleEl = card.querySelector(
                        '.entity-result__primary-subtitle, div[class*="primary-subtitle"], .t-14.t-normal'
                    );
                    const locEl = card.querySelector(
                        '.entity-result__secondary-subtitle, div[class*="secondary-subtitle"], .t-14.t-normal:nth-of-type(2)'
                    );
                    const linkEl = card.querySelector('a[href*="/in/"]');

                    return {
                        name: nameEl ? nameEl.innerText.trim() : '',
                        title: titleEl ? titleEl.innerText.trim() : '',
                        location: locEl ? locEl.innerText.trim() : '',
                        profileUrl: linkEl ? linkEl.href.split('?')[0] : ''
                    };
                }).filter(l => l.name && l.name.length > 0 && l.name.length < 100);
            }"""
            )

            logger.info(f"LinkedIn: found {len(leads)} leads for '{query}'")
            return {
                "success": True,
                "output": {"leads": leads, "count": len(leads)},
                "error": None,
            }
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def visit_profile(self, url: str) -> dict:
        """Visit a LinkedIn profile and extract info."""
        try:
            await self.open()
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            profile = await self._page.evaluate(
                """() => ({
                name: (document.querySelector('h1') || {}).innerText || '',
                headline: (document.querySelector('.text-body-medium.break-words') || {}).innerText || '',
                about: (document.querySelector('#about ~ div .full-width, section.pv-about-section') || {}).innerText || '',
                location: (document.querySelector('.text-body-small.inline.t-black--light.break-words') || {}).innerText || '',
                experience: Array.from(
                    document.querySelectorAll('#experience ~ div .pvs-entity, [id*="experience"] li')
                ).slice(0, 5).map(e => e.innerText.substring(0, 200)),
                connectionDegree: (document.querySelector('.dist-value, .pvs-header__optional-link') || {}).innerText || ''
            })"""
            )
            await human_delay()
            return {"success": True, "output": profile, "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def send_connection_request(self, url: str, note: str = "") -> dict:
        """Visit a profile and send a connection request with an optional note."""
        try:
            self._check_reset_daily()
            limit = cfg.RATE_LIMITS["linkedin_connections_per_day"]
            if self._daily_connections >= limit:
                return {
                    "success": False,
                    "output": None,
                    "error": f"Daily connection limit reached ({limit}). Try again tomorrow.",
                }

            await self.open()
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Look for Connect button
            connect_btn = await self._page.query_selector(
                'button[aria-label*="Connect"], button[aria-label*="connect"]'
            )
            if not connect_btn:
                # May be hidden in "More" dropdown
                more_btn = await self._page.query_selector(
                    'button[aria-label*="More actions"]'
                )
                if more_btn:
                    await more_btn.click()
                    await asyncio.sleep(1)
                    connect_btn = await self._page.query_selector(
                        '[aria-label*="Connect"], [data-control-name="connect"]'
                    )

            if not connect_btn:
                return {
                    "success": False,
                    "output": None,
                    "error": "Connect button not found. May already be connected.",
                }

            await connect_btn.click()
            await asyncio.sleep(1.5)

            # Add a note if provided
            if note:
                add_note_btn = await self._page.query_selector(
                    '[aria-label="Add a note"], button:has-text("Add a note")'
                )
                if add_note_btn:
                    await add_note_btn.click()
                    await asyncio.sleep(0.5)
                    note_field = await self._page.query_selector(
                        '#custom-message, textarea[name="message"]'
                    )
                    if note_field:
                        await note_field.fill(note[:300])  # LinkedIn 300 char limit
                        await human_delay()

            # Click Send
            send_btn = await self._page.query_selector(
                '[aria-label="Send invitation"], [aria-label="Send now"], button:has-text("Send")'
            )
            if send_btn:
                await send_btn.click()
                self._daily_connections += 1
                await human_delay()
                return {
                    "success": True,
                    "output": f"Connection request sent ({self._daily_connections}/{limit} today)",
                    "error": None,
                }

            return {
                "success": False,
                "output": None,
                "error": "Could not find Send button",
            }
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def send_message(self, profile_url: str, message: str) -> dict:
        """Send a direct message to a LinkedIn connection."""
        try:
            await self.open()
            await self._page.goto(profile_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            msg_btn = await self._page.query_selector(
                'button[aria-label*="Message"]'
            )
            if not msg_btn:
                return {
                    "success": False,
                    "output": None,
                    "error": "Message button not found. May not be a connection.",
                }

            await msg_btn.click()
            await asyncio.sleep(2)

            # Type in the message compose area
            msg_box = await self._page.wait_for_selector(
                '.msg-form__contenteditable, [role="textbox"][aria-label*="message"]',
                timeout=5000,
            )
            await msg_box.click()
            await msg_box.type(message, delay=25)
            await human_delay(0.5, 1.0)

            # Send
            await self._page.keyboard.press("Enter")
            await human_delay()

            return {
                "success": True,
                "output": f"Message sent to {profile_url}",
                "error": None,
            }
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    # ── JOB SEARCH & APPLICATION ──────────────────────────────────

    async def search_jobs(
        self, title: str, location: str = "", remote: bool = False
    ) -> dict:
        """Search for jobs on LinkedIn."""
        try:
            await self.open()
            encoded_title = quote_plus(title)
            url = f"{self.BASE_URL}/jobs/search/?keywords={encoded_title}"
            if location:
                url += f"&location={quote_plus(location)}"
            if remote:
                url += "&f_WT=2"

            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # LinkedIn lazy-loads — wait + scroll to trigger render
            await asyncio.sleep(4)
            await self._page.evaluate("window.scrollBy(0, 500)")
            await asyncio.sleep(2)

            jobs = await self._page.evaluate(
                """() => {
                // Strategy 1: job cards
                let cards = document.querySelectorAll('.jobs-search__results-list li, .job-card-container, [data-job-id]');

                // Strategy 2: scaffold cards
                if (!cards || cards.length === 0) {
                    cards = document.querySelectorAll('.scaffold-layout__list-container li, [class*="job-card"]');
                }

                // Strategy 3: any li with job view links
                if (!cards || cards.length === 0) {
                    cards = document.querySelectorAll('li:has(a[href*="/jobs/view/"])');
                }

                // Strategy 4: broadest fallback — find all job links
                if (!cards || cards.length === 0) {
                    const links = document.querySelectorAll('a[href*="/jobs/view/"]');
                    const seen = new Set();
                    return Array.from(links).map(a => {
                        const href = a.href.split('?')[0];
                        if (seen.has(href)) return null;
                        seen.add(href);
                        const container = a.closest('li, div[class*="card"]') || a.parentElement;
                        return {
                            title: a.innerText.trim() || (container.querySelector('[class*="title"]') || {}).innerText || '',
                            company: (container.querySelector('[class*="subtitle"], [class*="company"]') || {}).innerText || '',
                            location: (container.querySelector('[class*="location"], [class*="metadata"]') || {}).innerText || '',
                            link: href,
                            easyApply: !!container.querySelector('[class*="easy-apply"]')
                        };
                    }).filter(j => j && j.title && j.title.length < 200);
                }

                return Array.from(cards).slice(0, 20).map(job => ({
                    title: (job.querySelector('.base-search-card__title, .job-card-list__title, [class*="title"] a, a[href*="/jobs/view/"]') || {}).innerText || '',
                    company: (job.querySelector('.base-search-card__subtitle, .job-card-container__primary-description, [class*="company"], [class*="subtitle"]') || {}).innerText || '',
                    location: (job.querySelector('.job-search-card__location, .job-card-container__metadata-item, [class*="location"]') || {}).innerText || '',
                    link: (job.querySelector('a[href*="/jobs/view/"], a.base-card__full-link') || {}).href || '',
                    easyApply: !!job.querySelector('[class*="easy-apply"], .job-card-container__apply-method')
                })).filter(j => j.title);
            }"""
            )

            logger.info(f"LinkedIn: found {len(jobs)} jobs for '{title}'")
            return {
                "success": True,
                "output": {"jobs": jobs, "count": len(jobs)},
                "error": None,
            }
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def easy_apply(
        self, job_url: str, resume_path: str = "", answers: dict = None
    ) -> dict:
        """
        Apply to a job via LinkedIn Easy Apply with multi-step form handling.

        answers = {"years of experience": "3", "authorized to work": "Yes"}
        """
        try:
            self._check_reset_daily()
            limit = cfg.RATE_LIMITS["linkedin_applications_per_day"]
            if self._daily_applications >= limit:
                return {
                    "success": False,
                    "output": None,
                    "error": f"Daily application limit reached ({limit}). Try again tomorrow.",
                }

            resume = resume_path or cfg.USER_PROFILE.get("resume_path", "")
            answers = answers or {}

            await self.open()
            await self._page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Click Easy Apply button
            easy_btn = await self._page.query_selector(
                'button[aria-label*="Easy Apply"], .jobs-apply-button'
            )
            if not easy_btn:
                return {
                    "success": False,
                    "output": None,
                    "error": "No Easy Apply button found for this job.",
                }

            await easy_btn.click()
            await asyncio.sleep(2)

            # Walk through multi-step form
            max_steps = 10
            for step in range(max_steps):
                await asyncio.sleep(1.5)

                # Upload resume if file input exists and we have a resume
                if resume:
                    file_input = await self._page.query_selector('input[type="file"]')
                    if file_input:
                        await file_input.set_input_files(resume)
                        await asyncio.sleep(1)

                # Fill text inputs using answer matching
                inputs = await self._page.query_selector_all(
                    'input[type="text"], input[type="number"], textarea'
                )
                for inp in inputs:
                    label = await inp.get_attribute("aria-label") or ""
                    placeholder = await inp.get_attribute("placeholder") or ""
                    combined = f"{label} {placeholder}".lower()
                    for question, answer in answers.items():
                        if question.lower() in combined:
                            await inp.fill(str(answer))

                # Handle radio buttons / dropdowns
                selects = await self._page.query_selector_all("select")
                for sel in selects:
                    label = await sel.get_attribute("aria-label") or ""
                    for question, answer in answers.items():
                        if question.lower() in label.lower():
                            await sel.select_option(label=answer)

                # Check for Submit or Next
                submit_btn = await self._page.query_selector(
                    'button[aria-label="Submit application"], button:has-text("Submit application")'
                )
                next_btn = await self._page.query_selector(
                    'button[aria-label="Continue to next step"], button:has-text("Next")'
                )
                review_btn = await self._page.query_selector(
                    'button[aria-label="Review your application"], button:has-text("Review")'
                )

                if submit_btn:
                    await submit_btn.click()
                    self._daily_applications += 1
                    await human_delay()
                    return {
                        "success": True,
                        "output": f"✅ Applied! ({self._daily_applications}/{limit} today)",
                        "error": None,
                    }
                elif review_btn:
                    await review_btn.click()
                elif next_btn:
                    await next_btn.click()
                else:
                    break

            return {
                "success": False,
                "output": None,
                "error": "Stopped — form may need manual review.",
            }
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}
