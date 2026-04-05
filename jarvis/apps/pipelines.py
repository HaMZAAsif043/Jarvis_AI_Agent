"""
Automation Pipelines — End-to-end workflows combining app agents + content gen.

These are high-level orchestrations that chain multiple tools together:
- Upwork outreach: search → score → write cover letter → submit proposal
- LinkedIn lead gen: search → visit profile → write note → send connection
- Email triage: read inbox → summarize → flag urgent
"""

import asyncio
import logging
from typing import Optional

import jarvis.config as cfg
from jarvis.apps.linkedin import LinkedInAgent
from jarvis.apps.upwork import UpworkAgent
from jarvis.apps.gmail import GmailWeb
from jarvis.agent.content_gen import ContentGenerator
from jarvis.tools.chrome_cdp import human_delay

logger = logging.getLogger(__name__)


class AutomationPipelines:
    """High-level automation pipelines that combine app agents + LLM."""

    def __init__(self):
        self._linkedin: Optional[LinkedInAgent] = None
        self._upwork: Optional[UpworkAgent] = None
        self._gmail: Optional[GmailWeb] = None
        self._content: Optional[ContentGenerator] = None

    def _get_linkedin(self) -> LinkedInAgent:
        if self._linkedin is None:
            self._linkedin = LinkedInAgent()
        return self._linkedin

    def _get_upwork(self) -> UpworkAgent:
        if self._upwork is None:
            self._upwork = UpworkAgent()
        return self._upwork

    def _get_gmail(self) -> GmailWeb:
        if self._gmail is None:
            self._gmail = GmailWeb()
        return self._gmail

    def _get_content(self) -> ContentGenerator:
        if self._content is None:
            self._content = ContentGenerator()
        return self._content

    async def upwork_outreach(
        self,
        query: str,
        min_score: int = 7,
        bid_amount: float = 500,
        bid_type: str = "fixed",
        max_proposals: int = 5,
        custom_skills: list = None,
    ) -> dict:
        """
        Full Upwork outreach pipeline:
        1. Search for jobs matching the query
        2. Score each job for fit using LLM
        3. Generate personalized cover letters for good fits
        4. Submit proposals automatically

        Returns a summary of all actions taken.
        """
        try:
            upwork = self._get_upwork()
            content = self._get_content()
            results = {"applied": [], "skipped": [], "errors": []}

            # 1. Search jobs
            search_result = await upwork.search_jobs(query)
            if not search_result["success"]:
                return {
                    "success": False,
                    "output": None,
                    "error": f"Job search failed: {search_result['error']}",
                }

            jobs = search_result["output"]["jobs"]
            logger.info(f"Pipeline: found {len(jobs)} Upwork jobs for '{query}'")

            proposals_sent = 0
            for job in jobs:
                if proposals_sent >= max_proposals:
                    break

                # 2. Score the job
                score_result = await content.score_job_fit(job, custom_skills)
                if not score_result["success"]:
                    results["errors"].append(
                        {"title": job["title"], "error": score_result["error"]}
                    )
                    continue

                score = score_result["output"]["score"]
                reason = score_result["output"]["reason"]

                if score < min_score:
                    results["skipped"].append(
                        {
                            "title": job["title"],
                            "score": score,
                            "reason": reason,
                        }
                    )
                    logger.info(f"⏭️ Skipped: {job['title']} (score: {score})")
                    continue

                # 3. Generate cover letter
                cover_result = await content.generate_cover_letter(
                    job.get("description", job.get("title", ""))
                )
                if not cover_result["success"]:
                    results["errors"].append(
                        {"title": job["title"], "error": cover_result["error"]}
                    )
                    continue

                cover_letter = cover_result["output"]

                # 4. Submit proposal
                if job.get("link"):
                    proposal_result = await upwork.send_proposal(
                        job["link"], cover_letter, bid_amount, bid_type
                    )
                    if proposal_result["success"]:
                        results["applied"].append(
                            {
                                "title": job["title"],
                                "score": score,
                                "bid": bid_amount,
                            }
                        )
                        proposals_sent += 1
                        logger.info(
                            f"✅ Applied: {job['title']} (score: {score})"
                        )
                    else:
                        results["errors"].append(
                            {
                                "title": job["title"],
                                "error": proposal_result["error"],
                            }
                        )

                    await human_delay(3.0, 6.0)  # Longer delay between proposals

            summary = (
                f"Pipeline complete! "
                f"Applied: {len(results['applied'])}, "
                f"Skipped: {len(results['skipped'])}, "
                f"Errors: {len(results['errors'])}"
            )
            return {"success": True, "output": results, "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def linkedin_lead_gen(
        self,
        search_query: str,
        offer: str = "",
        max_connections: int = 10,
    ) -> dict:
        """
        Full LinkedIn lead gen pipeline:
        1. Search for people matching the query
        2. Visit each profile
        3. Generate personalized connection note via LLM
        4. Send connection request with note

        Returns a summary of all actions taken.
        """
        try:
            linkedin = self._get_linkedin()
            content = self._get_content()
            results = {"connected": [], "skipped": [], "errors": []}

            # 1. Search for leads
            search_result = await linkedin.search_leads(search_query)
            if not search_result["success"]:
                return {
                    "success": False,
                    "output": None,
                    "error": f"Lead search failed: {search_result['error']}",
                }

            leads = search_result["output"]["leads"]
            logger.info(f"Pipeline: found {len(leads)} LinkedIn leads for '{search_query}'")

            connections_sent = 0
            for lead in leads:
                if connections_sent >= max_connections:
                    break

                if not lead.get("profileUrl"):
                    continue

                # 2. Visit profile to get more info
                profile_result = await linkedin.visit_profile(lead["profileUrl"])
                if not profile_result["success"]:
                    results["errors"].append(
                        {"name": lead["name"], "error": profile_result["error"]}
                    )
                    continue

                profile = profile_result["output"]

                # 3. Generate personalized connection note
                note_result = await content.generate_connection_note(
                    profile, offer=offer
                )
                note = note_result["output"] if note_result["success"] else ""

                # 4. Send connection request
                conn_result = await linkedin.send_connection_request(
                    lead["profileUrl"], note=note
                )
                if conn_result["success"]:
                    results["connected"].append(
                        {
                            "name": lead["name"],
                            "title": lead.get("title", ""),
                        }
                    )
                    connections_sent += 1
                    logger.info(f"✅ Connected: {lead['name']}")
                else:
                    results["skipped"].append(
                        {
                            "name": lead["name"],
                            "reason": conn_result["error"],
                        }
                    )

                await human_delay(5.0, 10.0)  # Longer delay for LinkedIn

            summary = (
                f"Pipeline complete! "
                f"Connected: {len(results['connected'])}, "
                f"Skipped: {len(results['skipped'])}, "
                f"Errors: {len(results['errors'])}"
            )
            return {"success": True, "output": results, "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def email_triage(self, count: int = 10) -> dict:
        """
        Email triage pipeline:
        1. Read latest emails from inbox
        2. Summarize them with LLM
        3. Flag urgent items

        Returns organized email summary.
        """
        try:
            gmail = self._get_gmail()
            content = self._get_content()

            # 1. Read latest emails
            read_result = await gmail.read_latest_emails(count=count)
            if not read_result["success"]:
                return {
                    "success": False,
                    "output": None,
                    "error": f"Failed to read emails: {read_result['error']}",
                }

            emails = read_result["output"]
            if not emails:
                return {
                    "success": True,
                    "output": "No emails found in inbox.",
                    "error": None,
                }

            # 2. Summarize with LLM
            summary_result = await content.summarize_emails(emails)
            if not summary_result["success"]:
                # Return raw emails as fallback
                return {
                    "success": True,
                    "output": {
                        "emails": emails,
                        "summary": "(LLM summary unavailable)",
                    },
                    "error": None,
                }

            return {
                "success": True,
                "output": {
                    "email_count": len(emails),
                    "summary": summary_result["output"],
                    "emails": emails,
                },
                "error": None,
            }
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}
