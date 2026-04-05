"""
Content Generator — LLM-powered content for outreach automation.

Uses Gemini to write:
- Personalized Upwork cover letters
- LinkedIn connection notes
- Job fit scoring
- Follow-up messages
- Email summaries
"""

import asyncio
import logging
import time

import google.genai as genai
from google.genai import types

import jarvis.config as cfg

logger = logging.getLogger(__name__)


class ContentGenerator:
    """Gemini-powered content generation for outreach and applications."""

    MAX_RETRIES = 5

    def __init__(self):
        key = cfg.GEMINI_API_KEY
        if not key:
            raise ValueError("GEMINI_API_KEY not set")
        self.client = genai.Client(api_key=key)
        self.model = cfg.GEMINI_MODEL or "gemini-2.0-flash"
        self.profile = cfg.USER_PROFILE

    def _call_llm(self, prompt: str, max_tokens: int = 500) -> str:
        """Call Gemini with retry logic."""
        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.7,
                        max_output_tokens=max_tokens,
                    ),
                )
                return response.text.strip()
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                if any(
                    code in error_str
                    for code in ["503", "429", "500", "unavailable", "overloaded"]
                ):
                    wait = min(10, 2**attempt)
                    logger.warning(
                        f"Content gen API error (attempt {attempt}): {e}. Retry in {wait}s"
                    )
                    time.sleep(wait)
                    continue
                raise
        raise last_error

    async def generate_cover_letter(
        self, job_description: str, custom_profile: str = ""
    ) -> dict:
        """Generate a personalized Upwork cover letter."""
        try:
            profile_text = custom_profile or self.profile["bio"]
            prompt = f"""Write a short, personalized Upwork cover letter.

Job description:
{job_description}

My profile:
{profile_text}

Skills: {', '.join(self.profile['skills'])}

Rules:
- Under 150 words
- Start with a specific observation about THEIR project (not about yourself)
- Mention ONE relevant past project or skill that directly applies
- End with a clear call-to-action
- NO generic openers like "I am writing to apply" or "Dear Hiring Manager"
- Sound human, confident, and direct — not corporate
- Do NOT use bullet points
"""
            text = await asyncio.to_thread(self._call_llm, prompt, 400)
            return {"success": True, "output": text, "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def generate_connection_note(
        self, profile_data: dict, offer: str = ""
    ) -> dict:
        """Generate a LinkedIn connection note (under 300 chars)."""
        try:
            offer_text = offer or "AI automation services"
            prompt = f"""Write a LinkedIn connection note.

Their profile:
- Name: {profile_data.get('name', 'Unknown')}
- Headline: {profile_data.get('headline', '')}
- Location: {profile_data.get('location', '')}

My offer: {offer_text}

Rules:
- UNDER 300 characters (this is a HARD limit — LinkedIn will reject longer notes)
- Sound human and genuine, NOT salesy
- Reference something specific about THEIR work if possible
- End with a soft reason to connect
- NO emojis, NO links
"""
            text = await asyncio.to_thread(self._call_llm, prompt, 200)
            # Enforce 300 char limit
            if len(text) > 300:
                text = text[:297] + "..."
            return {"success": True, "output": text, "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def score_job_fit(self, job: dict, custom_skills: list = None) -> dict:
        """Score how well a job matches the user's skills (1-10)."""
        try:
            skills = custom_skills or self.profile["skills"]
            prompt = f"""Score this job 1-10 for how well it fits my skills.

Job:
  Title: {job.get('title', '')}
  Description: {job.get('description', '')}
  Budget: {job.get('budget', '')}
  Skills required: {job.get('skills', [])}

My skills: {', '.join(skills)}

Respond with ONLY a JSON object:
{{"score": <1-10>, "reason": "<one sentence why>"}}
"""
            text = await asyncio.to_thread(self._call_llm, prompt, 100)
            # Parse the score
            import json
            import re

            # Try JSON parse
            try:
                result = json.loads(text)
                score = int(result.get("score", 0))
                reason = result.get("reason", "")
            except (json.JSONDecodeError, ValueError):
                # Fallback: extract number
                numbers = re.findall(r"\d+", text)
                score = int(numbers[0]) if numbers else 5
                reason = text

            return {
                "success": True,
                "output": {"score": min(10, max(1, score)), "reason": reason},
                "error": None,
            }
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def generate_followup_message(
        self, context: str, platform: str = "linkedin"
    ) -> dict:
        """Generate a follow-up DM based on previous interaction context."""
        try:
            prompt = f"""Write a brief follow-up message for {platform}.

Context of previous interaction:
{context}

My profile: {self.profile['bio']}

Rules:
- Under 100 words
- Reference the previous interaction naturally
- Provide value (not just "checking in")
- End with a question to keep the conversation going
- Sound human and personable
"""
            text = await asyncio.to_thread(self._call_llm, prompt, 200)
            return {"success": True, "output": text, "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def summarize_emails(self, emails: list) -> dict:
        """Summarize a list of emails and flag urgent ones."""
        try:
            email_text = "\n\n".join(
                f"From: {e.get('from', '?')} | Subject: {e.get('subject', '?')}\n"
                f"Preview: {e.get('preview', '')}"
                for e in emails
            )
            prompt = f"""Summarize these emails and flag any urgent ones.

Emails:
{email_text}

Respond with:
1. A 2-3 sentence overall summary
2. A list of urgent items (if any) that need immediate attention
3. Any items that can wait
"""
            text = await asyncio.to_thread(self._call_llm, prompt, 500)
            return {"success": True, "output": text, "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    async def generate_email_reply(
        self, email_body: str, intent: str = "professional"
    ) -> dict:
        """Generate a reply to an email."""
        try:
            prompt = f"""Write a reply to this email.

Email body:
{email_body[:2000]}

Intent: {intent}
My name: {self.profile['name']}
My role: {self.profile['title']} at {self.profile['company']}

Rules:
- Match the tone of the original email
- Be concise but thorough
- End with a clear next step
"""
            text = await asyncio.to_thread(self._call_llm, prompt, 400)
            return {"success": True, "output": text, "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}
