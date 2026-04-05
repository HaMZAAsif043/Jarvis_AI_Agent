import asyncio
import json
import logging
import google.genai as genai
from google.genai import types

import jarvis.config as cfg

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are JARVIS, an AI desktop assistant. You can control the user's PC through tools.

RULES:
1. For casual chat, just respond naturally with no tool calls.
2. For actionable tasks, respond with a JSON object containing tool_calls.
3. You may call multiple tools in sequence — output them as a list.
4. Think step by step about which tool to use.
5. Use wait(seconds) between actions when needed (e.g., wait for UI to load).

RESPONSE FORMAT:
If the request is just conversation (greeting, question about you, etc.), respond with plain text.
If the request requires action, respond ONLY with a valid JSON object in this exact structure:
{"thought": "your reasoning here", "tool_calls": [{"tool": "tool_name", "action": "method_name", "params": {"arg": "value"}}]}

AVAILABLE TOOLS:
- tool: "file_manager"
  actions: read_file(path), write_file(path, content), copy_file(source, destination), move_file(source, destination), delete_file(path), list_dir(path), search_files(path, pattern)

- tool: "browser"
  actions: open_url(url), screenshot(output_path), get_page_text(url), click_element(selector), fill_form(selector, value), submit_form(button_selector), get_element_text(selector), get_html(), wait(seconds), go_back(), get_page_title(), select_option(selector, value)

- tool: "desktop"
  actions: mouse_click(x, y, button), mouse_move(x, y), mouse_drag(start_x, start_y, end_x, end_y), drag_drop(start_x, start_y, end_x, end_y), mouse_scroll(clicks, direction), right_click(x, y), double_click(x, y), keyboard_type(text), press_key(key), hotkey(*keys), wait(seconds), screenshot(output_path), get_screen_size(), list_windows(), focus_window(title), locate_on_screen(image_path), click_at_image(image_path), get_cursor_position(), copy_to_clipboard(text), paste_from_clipboard()

- tool: "terminal"
  actions: run(command)

TIPS:
- To fill a form and submit: call fill_form then submit_form
- To drag-and-drop a file: use drag_drop with source and destination screen coordinates
- To find something on screen by image: use locate_on_screen then mouse_click on the returned coordinates
- To take a screenshot of specific UI area: take screenshot then use mouse_click on coordinates
- To wait between actions for page/UI to load: use wait(seconds=2) or wait(seconds=3)
"""


class Brain:
    """Gemini LLM wrapper with ReAct tool-use support."""

    def __init__(self, api_key: str | None = None):
        key = api_key or cfg.GEMINI_API_KEY
        if not key:
            raise ValueError("GEMINI_API_KEY not set. Set it in .env or config.py")
        self.client = genai.Client(api_key=key)
        self.model_name = cfg.GEMINI_MODEL
        # Internal history: list of {"role": "user"|"model", "text": "..."}
        self.chat_history: list[dict] = []

    def _build_history(self, max_entries: int = 20) -> list:
        """Convert internal chat_history to google-genai Content list for chat history."""
        result = []
        for entry in self.chat_history[-max_entries:]:
            role = entry["role"]
            if role == "assistant":
                role = "model"
            result.append(types.Content(role=role, parts=[types.Part(text=entry["text"])]))
        return result

    def _get_chat(self, max_entries: int = 20):
        """Get a chat instance with history already loaded."""
        history = self._build_history(max_entries)
        chat = self.client.chats.create(model=self.model_name, history=history)
        return chat

    def plan_action(self, user_input: str) -> dict:
        """Get Gemini's plan as a JSON tool-call dict, or chat response."""
        chat = self._get_chat()

        prompt = f"USER REQUEST: {user_input}\n\nDecide if this requires tool calls or is just conversation. If action needed, respond with JSON only."

        response = chat.send_message(
            prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
            ),
        )
        text = response.text.strip()

        # Try parsing as JSON
        try:
            if text.startswith("```"):
                lines = text.split("\n")
                lines = [l for l in lines if not l.startswith("```")]
                text = "\n".join(lines).strip()
            parsed = json.loads(text)
            if isinstance(parsed, dict) and "tool_calls" in parsed:
                self.chat_history.append({"role": "user", "text": user_input})
                self.chat_history.append({"role": "assistant", "text": text})
                return parsed
        except (json.JSONDecodeError, Exception) as e:
            logger.debug(f"Not valid JSON: {e}")

        # Fall back: treat as chat
        self.chat_history.append({"role": "user", "text": user_input})
        self.chat_history.append({"role": "assistant", "text": text})
        return {"thought": text, "tool_calls": []}

    def chat_response(self, message: str) -> str:
        """Conversational response with history."""
        chat = self._get_chat()

        response = chat.send_message(
            message,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
            ),
        )
        reply = response.text.strip()

        self.chat_history.append({"role": "user", "text": message})
        self.chat_history.append({"role": "assistant", "text": reply})
        return reply

    async def execute_command(self, user_input: str, tool_router=None, callback=None) -> dict:
        """
        ReAct execution loop: plan → execute → observe → re-plan until done.

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

        for i in range(max_iters):
            # 1. Get Gemini's plan
            plan = self.plan_action(user_input)
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
                await callback("thinking", {"message": f"Step {min(len(steps)+1, 10)}: {thought[:100]}..."} if len(thought) > 100 else {"message": thought})

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

            # 4. Check if all steps succeeded in the last batch
            all_succeeded = all(r.get("success", False) for r in results)
            last_result = results[-1] if results else {}

            # 5. Format results for Gemini feedback
            formatted = []
            for r in results:
                if r.get("success"):
                    formatted.append(f"[{r['tool']}] SUCCESS: {r.get('output', 'done')}")
                else:
                    formatted.append(f"[{r['tool']}] FAILED: {r.get('error', 'unknown error')}")
            result_text = "\n".join(formatted)

            # 6. Feed results back to Gemini for next iteration
            self.chat_history.append({
                "role": "user",
                "text": (
                    f"Results from previous step:\n{result_text}\n\n"
                    f"Decide what to do next. If the task is fully complete, respond with just text "
                    f"(no tool_calls). Original task was: {original_input}"
                ),
            })

            # Prepare next iteration input
            user_input = (
                f"Continue from previous results. Original task: {original_input}. "
                f"Provide the next step or conclude the task."
            )

            # If the last batch was all successful and only had 1-2 simple steps,
            # let Gemini decide if more work is needed (normal loop continuation)

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
