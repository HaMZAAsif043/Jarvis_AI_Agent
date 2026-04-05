import asyncio
import json
import logging
import re
import time
import google.genai as genai
from google.genai import types

import jarvis.config as cfg

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are JARVIS — a highly capable, autonomous AI assistant that fully controls the user's Windows PC.
You don't just open apps — you COMPLETE tasks end-to-end. You are proactive, smart, and persistent.

IDENTITY:
- You are like the JARVIS from Iron Man — intelligent, resourceful, and always follow through.
- When the user asks you to do something, you do the WHOLE thing, not just the first step.
- If something fails, you try alternative approaches automatically.

RESPONSE RULES:
1. For casual chat ONLY (greetings, small talk): respond with plain text.
2. For ANY task: respond with ONLY a JSON object — no extra text.
3. You can and SHOULD chain multiple tool_calls in one response for multi-step actions.
4. After each step completes, you will get the results. Continue working until the task is FULLY done.

AGENTIC BEHAVIOR — THIS IS CRITICAL:
- NEVER just open something and stop. If the user says "play music", you must: open the app/site, wait for it to load, then actually start playback.
- BE FAST! Use desktop.wait(2) or desktop.wait(3) between steps. Do NOT use wait(10). Act quickly like a smart assistant!
- Use desktop.screenshot() to SEE what is on screen. The image will be sent to you in the next step automatically.
- Chain actions: open, wait, screenshot, analyze, click, verify.
- If you opened something, your job is NOT done until the user's GOAL is achieved.

═══════════════════════════════════════════════════════════════
TOOL SELECTION GUIDE — CHOOSE THE RIGHT TOOL FOR THE JOB
═══════════════════════════════════════════════════════════════

For LINKEDIN tasks → use the "linkedin" tool (NOT desktop clicks):
  - linkedin.search_leads(query, location) — find people
  - linkedin.visit_profile(url) — visit and extract profile data
  - linkedin.send_connection_request(url, note) — send connection with note
  - linkedin.send_message(profile_url, message) — DM a connection
  - linkedin.search_jobs(title, location, remote) — find jobs
  - linkedin.easy_apply(job_url, resume_path, answers) — apply to Easy Apply jobs

For UPWORK tasks → use the "upwork" tool:
  - upwork.search_jobs(query, filters) — search Upwork jobs
  - upwork.send_proposal(job_url, cover_letter, bid_amount, bid_type) — submit proposal
  - upwork.check_messages() — read Upwork messages
  - upwork.get_active_contracts() — list active contracts

For YOUTUBE tasks → use the "youtube" tool:
  - youtube.search(query) — search videos
  - youtube.watch_video(url) — play a video
  - youtube.post_comment(video_url, comment) — post comment
  - youtube.get_channel_videos(channel_url) — browse channel
  - youtube.get_video_info(url) — get video details

For WHATSAPP tasks → use the "whatsapp" tool:
  - whatsapp.send_message(contact, message) — send WA message
  - whatsapp.read_recent_messages(contact, count) — read chat history
  - whatsapp.get_chat_list() — list all chats
  - whatsapp.filter_unread() — show unread conversations
  - whatsapp.send_file(contact, filepath) — send a file

For GMAIL tasks → use the "gmail" tool:
  - gmail.compose(to, subject, body) — compose and send email
  - gmail.search_emails(query) — search emails
  - gmail.read_latest_emails(count) — read inbox
  - gmail.open_email(index) — open and read full email

For AI-GENERATED CONTENT → use the "content_gen" tool:
  - content_gen.generate_cover_letter(job_description) — write Upwork proposal
  - content_gen.generate_connection_note(profile_data, offer) — write LinkedIn note
  - content_gen.score_job_fit(job, custom_skills) — score job fit 1-10
  - content_gen.generate_followup_message(context, platform) — write follow-up DM
  - content_gen.summarize_emails(emails) — summarize and triage emails
  - content_gen.generate_email_reply(email_body, intent) — draft email reply

For FULL AUTOMATION PIPELINES → use the "pipeline" tool:
  - pipeline.upwork_outreach(query, min_score, bid_amount, bid_type, max_proposals) — search→score→apply
  - pipeline.linkedin_lead_gen(search_query, offer, max_connections) — search→visit→connect
  - pipeline.email_triage(count) — read→summarize→flag urgent

═══════════════════════════════════════════════════════════════
CORE TOOLS (desktop, files, browser, terminal)
═══════════════════════════════════════════════════════════════

- tool: "file_manager"
  actions: read_file(path), write_file(path, content), copy_file(source, destination), move_file(source, destination), delete_file(path), list_dir(path), search_files(path, pattern)

- tool: "browser" (HIDDEN headless — web scraping ONLY)
  actions: open_url(url), screenshot(output_path), get_page_text(url), click_element(selector), fill_form(selector, value), submit_form(button_selector), get_element_text(selector), get_html(), wait(seconds), go_back(), get_page_title(), select_option(selector, value)

- tool: "desktop" (interact with visible screen — mouse, keyboard, screenshots)
  actions: mouse_click(x, y, button), mouse_move(x, y), mouse_drag(start_x, start_y, end_x, end_y), drag_drop(start_x, start_y, end_x, end_y), mouse_scroll(clicks, direction), right_click(x, y), double_click(x, y), keyboard_type(text), press_key(key), hotkey(keys), wait(seconds), screenshot(output_path), get_screen_size(), list_windows(), focus_window(title), locate_on_screen(image_path), click_at_image(image_path), get_cursor_position(), copy_to_clipboard(text), paste_from_clipboard()

- tool: "terminal"
  actions: run(command)

═══════════════════════════════════════════════════════════════

RESPONSE FORMAT (for tasks — ONLY the JSON, nothing else):
{"thought": "reasoning", "tool_calls": [{"tool": "name", "action": "method", "params": {}}]}

TOOL SELECTION CRITICAL RULES:
- For WhatsApp/Gmail/LinkedIn/Upwork/YouTube → ALWAYS use the dedicated app tool first!
  They connect to Chrome CDP directly — way more reliable than desktop clicks.
- Only fall back to desktop.screenshot + desktop.mouse_click for apps NOT listed above.
- For content writing tasks → use content_gen tool to generate quality text with LLM.
- For full automation flows → use pipeline tool to chain everything automatically.

MULTI-STEP EXAMPLES:

User: "send WhatsApp message to Ali saying deployment is done"
{"thought": "Using whatsapp tool to send message to Ali.", "tool_calls": [{"tool": "whatsapp", "action": "send_message", "params": {"contact": "Ali", "message": "Hey Ali, deployment is done! You can check it now."}}]}

User: "find Upwork jobs for AI voice agents and apply to the best ones"
{"thought": "Using pipeline for full Upwork outreach — search, score, generate cover letters, and apply.", "tool_calls": [{"tool": "pipeline", "action": "upwork_outreach", "params": {"query": "AI voice agent", "min_score": 7, "bid_amount": 500, "max_proposals": 5}}]}

User: "find dental clinic owners on LinkedIn and send connection requests"
{"thought": "Using LinkedIn lead gen pipeline — search, visit profiles, write personalized notes, connect.", "tool_calls": [{"tool": "pipeline", "action": "linkedin_lead_gen", "params": {"search_query": "dental clinic owner", "offer": "AI voice receptionist for dental clinics", "max_connections": 10}}]}

User: "check my unread Gmail and tell me if anything is urgent"
{"thought": "Using email triage pipeline to read, summarize, and flag urgent emails.", "tool_calls": [{"tool": "pipeline", "action": "email_triage", "params": {"count": 10}}]}

User: "write a cover letter for this Upwork job about building a Django API"
{"thought": "Using content_gen to write a personalized cover letter.", "tool_calls": [{"tool": "content_gen", "action": "generate_cover_letter", "params": {"job_description": "Need a Django API developer for building a REST API with authentication and payment integration"}}]}

User: "play music for me"
{"thought": "Using youtube tool to search for a music playlist and then watch the first video.", "tool_calls": [{"tool": "youtube", "action": "search", "params": {"query": "lofi hip hop radio live"}}]}

User: "hello"
Hello! I'm JARVIS, your AI desktop assistant. I can now automate LinkedIn, Upwork, WhatsApp, Gmail, YouTube, and more. What would you like me to do?

KEY PRINCIPLES:
- ALWAYS use dedicated app tools for LinkedIn/Upwork/YouTube/WhatsApp/Gmail.
- ALWAYS follow through — opening something is step 1, not the final step.
- Use desktop.screenshot to see the screen when using desktop tool.
- Chain multiple tool_calls in one response for speed.
- If a step fails, try alternative approaches — don't give up.
- For tasks, output ONLY the JSON object — no markdown, no extra text.
"""


def _extract_json(text: str) -> dict | None:
    """Robustly extract a JSON object from model output.

    Handles:
    - Pure JSON
    - JSON wrapped in ```json ... ``` code fences
    - JSON embedded in surrounding prose text
    """
    text = text.strip()

    # 1. Try direct parse
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # 2. Try extracting from markdown code fences
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fence_match:
        try:
            parsed = json.loads(fence_match.group(1).strip())
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    # 3. Try to find a JSON object anywhere in the text (greedy brace matching)
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        candidate = text[first_brace : last_brace + 1]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    return None


class Brain:
    """Gemini LLM wrapper with ReAct tool-use support."""

    MAX_API_RETRIES = 8  # Increased to gracefully handle 503 errors

    def __init__(self, api_key: str | None = None):
        key = api_key or cfg.GEMINI_API_KEY
        if not key:
            raise ValueError("GEMINI_API_KEY not set. Set it in .env or config.py")
        self.client = genai.Client(api_key=key)
        self.model_name = cfg.GEMINI_MODEL or "gemini-2.0-flash"
        if not self.model_name:
            raise ValueError("GEMINI_MODEL is required but empty. Set GEMINI_MODEL in .env")
        logger.info(f"Initialized Brain with model: {self.model_name}")
        self.chat_history: list[dict] = []

    def _format_history(self, max_entries: int = 20) -> str:
        """Format recent chat history as a readable conversation."""
        lines = []
        for entry in self.chat_history[-max_entries:]:
            role = "JARVIS" if entry["role"] == "assistant" else "USER"
            lines.append(f"{role}: {entry['text']}")
        return "\n".join(lines)

    def _call_gemini(self, contents: str | list) -> str:
        """Call Gemini API with retry on transient errors (503, 429, etc.)."""
        last_error = None
        for attempt in range(1, self.MAX_API_RETRIES + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.2,
                    ),
                )
                return response.text.strip()
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                if any(code in error_str for code in ["503", "429", "500", "unavailable", "overloaded", "high demand"]):
                    wait_time = min(10, 2 ** attempt)
                    logger.warning(f"API error (attempt {attempt}/{self.MAX_API_RETRIES}): {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                raise
        raise last_error

    def _plan_action_sync(self, user_input: str, attached_images: list = None) -> dict:
        """Synchronous Gemini call — will be run in a thread."""
        history_text = self._format_history()
        context = f"{history_text}\n\n" if history_text else ""
        prompt = (
            f"{context}CURRENT USER REQUEST: {user_input}\n\n"
            "If this request requires ANY action on the PC (files, terminal, browser, desktop, "
            "opening apps, playing music, searching, etc.), respond with ONLY the JSON object. "
            "If this is just casual conversation, respond with plain text."
        )

        if attached_images:
            prompt += "\n[System: Attached Screenshots for your reference. Look at them to understand the UI layout before deciding what to click.]"

        contents = [prompt]
        if attached_images:
            contents.extend(attached_images)

        try:
            text = self._call_gemini(contents)
        except Exception as e:
            error_msg = f"Sorry, I encountered an API error: {e}. Please try again."
            logger.error(f"Gemini API failed after retries: {e}")
            self.chat_history.append({"role": "user", "text": user_input})
            self.chat_history.append({"role": "assistant", "text": error_msg})
            return {"thought": error_msg, "tool_calls": []}

        logger.debug(f"Raw Gemini response:\n{text[:500]}")

        parsed = _extract_json(text)
        if parsed and "tool_calls" in parsed:
            self.chat_history.append({"role": "user", "text": user_input})
            self.chat_history.append({"role": "assistant", "text": json.dumps(parsed)})
            return parsed

        self.chat_history.append({"role": "user", "text": user_input})
        self.chat_history.append({"role": "assistant", "text": text})
        return {"thought": text, "tool_calls": []}

    async def plan_action(self, user_input: str, attached_images: list = None) -> dict:
        """Async wrapper — runs the blocking Gemini call in a thread."""
        return await asyncio.to_thread(self._plan_action_sync, user_input, attached_images)

    def chat_response(self, message: str) -> str:
        """Conversational response with history."""
        history_text = self._format_history()
        context = f"{history_text}\n\n" if history_text else ""

        try:
            reply = self._call_gemini(f"{context}USER: {message}")
        except Exception as e:
            reply = f"Sorry, I encountered an API error: {e}. Please try again."

        self.chat_history.append({"role": "user", "text": message})
        self.chat_history.append({"role": "assistant", "text": reply})
        return reply

    async def execute_command(self, user_input: str, tool_router=None, callback=None) -> dict:
        """
        ReAct execution loop: plan -> execute -> observe -> re-plan until done.

        Args:
            user_input: The user's command.
            tool_router: ToolRouter instance for executing tool calls. Created if None.
            callback: Optional async fn(event_type, data) for streaming events.

        Returns:
            dict with keys: success, thought, steps (list), summary (str)
        """
        from jarvis.agent.router import ToolRouter

        router = tool_router or ToolRouter(callback=callback)
        max_iters = cfg.MAX_ITERATIONS
        steps = []
        original_input = user_input
        created_router = tool_router is None
        attached_images = []

        for i in range(max_iters):
            # 1. Get Gemini's plan (async — doesn't block event loop)
            plan = await self.plan_action(user_input, attached_images=attached_images)
            thought = plan.get("thought", "")
            tool_calls = plan.get("tool_calls", [])

            # 2. No tools needed — conversational response or task is complete
            if not tool_calls:
                self.chat_history.append({
                    "role": "assistant",
                    "text": f"Task complete. {thought}" if steps else thought,
                })
                if not steps:
                    return {"success": True, "thought": thought, "steps": [], "summary": thought}
                return {
                    "success": True,
                    "thought": thought,
                    "steps": steps,
                    "summary": f"Completed in {len(steps)} step(s). Final note: {thought}",
                }

            # 3. Execute the plan
            if callback:
                msg = thought[:100] + "..." if len(thought) > 100 else thought
                await callback("thinking", {"message": f"Step {len(steps)+1}: {msg}"})

            results = await router.execute_plan(plan)

            for r in results:
                step_info = {
                    "step": len(steps) + 1,
                    "tool": r.get("tool", "unknown"),
                    "success": r.get("success", False),
                    "output": r.get("output"),
                    "error": r.get("error"),
                }
                steps.append(step_info)

            # 4. Format results for Gemini feedback
            formatted = []
            attached_images = []  # Reset for next iteration
            for r in results:
                if r.get("success"):
                    output_text = str(r.get('output', 'done'))
                    formatted.append(f"[{r['tool']}] SUCCESS: {output_text}")
                    if "Screenshot saved to" in output_text:
                        import re
                        m = re.search(r"Screenshot saved to (.+\.png)", output_text)
                        if m:
                            try:
                                import PIL.Image
                                img = PIL.Image.open(m.group(1))
                                img.load()  # Keep in memory
                                attached_images.append(img)
                            except Exception as e:
                                formatted.append(f"[System: failed to attach image: {e}]")
                else:
                    formatted.append(f"[{r['tool']}] FAILED: {r.get('error', 'unknown error')}")
            result_text = "\n".join(formatted)

            # 5. Feed results back — push the agent to KEEP GOING
            self.chat_history.append({
                "role": "user",
                "text": (
                    f"Results from previous step:\n{result_text}\n\n"
                    f"Original task: {original_input}\n\n"
                    f"Think carefully: has the user's GOAL been FULLY achieved? "
                    f"For example:\n"
                    f"- 'play music' = NOT done if you only opened a browser. You must also start playback.\n"
                    f"- 'open notepad and write X' = NOT done if you only opened notepad.\n"
                    f"- 'search for files' = DONE once you have the results to show.\n\n"
                    f"If more steps are needed, respond with the next JSON tool_calls. "
                    f"ONLY respond with plain text when the task is 100% complete."
                ),
            })

            # Prepare next iteration input
            user_input = (
                f"Continue working on the task: {original_input}. "
                f"What is the NEXT action needed to fully complete the user's request?"
            )

        # Max iterations reached
        summary = (
            f"Reached maximum iterations ({max_iters}). Completed {len(steps)} step(s):\n"
            + "\n".join(f"  Step {s['step']}: {s['tool']} {'OK' if s['success'] else 'FAILED'}" for s in steps)
        )
        self.chat_history.append({"role": "assistant", "text": summary})

        if created_router:
            await router.cleanup()

        return {
            "success": False,
            "thought": "Max iterations reached",
            "steps": steps,
            "summary": summary,
        }
