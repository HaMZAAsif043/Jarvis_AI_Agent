# Roadmap

## Current State

JARVIS has a solid skeleton: Gemini brain (single-shot planning), tool router (browser/desktop/file/terminal), SQLite memory (task history), scheduler (APScheduler), and a FastAPI web dashboard with WebSocket streaming. All tool modules have basic implementations that work but have gaps.

The critical gap: **the agent is single-shot**. It plans once and executes. It does NOT loop, observe results, adapt, or re-plan. That's the difference between "can run tools" and "can autonomously complete any task."

---

## Phases

### Phase 1: Autonomous Execution Loop (ReAct)
**Goal:** Transform single-shot planning into a multi-step autonomous execution loop where JARVIS can observe tool results, adapt, and continue executing until the task is complete.
**Requirements:** AUTO-01, AUTO-02, AUTO-03, REL-02
**Success Criteria:**
1. User gives a multi-step command like "find all PDFs on my desktop, copy them to C:\Documents" and JARVIS plans, executes each step, observes results, and reports completion
2. When a step fails, JARVIS automatically retries or tries an alternative approach
3. The loop has a configurable max-iterations guard to prevent infinite loops
4. Final natural-language summary of what was accomplished

**UI hint:** no

### Phase 2: Enhanced Tool Capabilities
**Goal:** Fill gaps in all four tool modules to make them production-ready for autonomous use.
**Requirements:** FILE-03, TERM-02, TERM-03, DESK-03
**Success Criteria:**
1. File manager supports content-based search (search inside files, not just filenames) and filetype filtering (PDF, DOCX, etc.)
2. Terminal supports process management (list running processes, kill process, manage venvs)
3. Desktop supports reliable element detection and error handling for screen interactions
4. All tools return structured, parseable results the brain can act on

**UI hint:** no

### Phase 3: Persistent Memory & Context
**Goal:** Implement cross-session memory so JARVIS remembers preferences, past tasks, and learned patterns, and feeds this context into planning.
**Requirements:** MEM-01, MEM-02, MEM-03, REL-01
**Success Criteria:**
1. JARVIS stores user preferences (e.g., "always search in D:\Downloads") and loads them at startup
2. JARVIS can reference past tasks when asked ("find the files you found yesterday")
3. Conversation context from the current session is injected into the brain's system prompt for each new command
4. Memory is queryable with semantic search, not just text LIKE matching

**UI hint:** no

### Phase 4: Enhanced Brain & System Prompt
**Goal:** Upgrade the Gemini brain with structured tool definitions, better reasoning, error recovery logic, and a comprehensive system prompt that covers all available capabilities.
**Requirements:** AUTO-01, AUTO-02, REL-02, REL-03
**Success Criteria:**
1. Brain uses Gemini's native function calling API (not JSON text parsing) for reliable tool invocation
2. System prompt accurately describes every tool, action, and parameter
3. Brain can handle ambiguous requests by asking clarifying questions
4. Destructive actions require explicit confirmation before execution

**UI hint:** no

### Phase 5: Web Dashboard Enhancements
**Goal:** Build a polished web UI for sending commands, viewing real-time execution, managing scheduled tasks, and browsing execution history.
**Requirements:** WEB-01, WEB-02, WEB-03, SCHED-01, SCHED-02
**Success Criteria:**
1. Clean command interface with real-time streaming of tool execution steps
2. Task history page with search and filtering
3. Scheduler management: add/edit/delete scheduled tasks via UI
4. Execution results displayed in readable format (not raw JSON)

**UI hint:** yes

### Phase 6: Production Hardening & Configuration
**Goal:** Make JARVIS production-ready with proper config management, logging, error handling, and startup/shutdown scripts.
**Requirements:** CFG-01, REL-01, SCHED-02
**Success Criteria:**
1. `.env` configuration covers all settings (API key, model, server, memory, scheduler persistence)
2. Structured logging to file with rotation
3. Proper startup/shutdown with graceful process cleanup
4. One-command startup scripts (`.bat` for Windows) for easy use
5. README with complete setup and usage instructions

**UI hint:** no

---

## Requirement Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTO-01 | Phase 1, 4 | — |
| AUTO-02 | Phase 1 | — |
| AUTO-03 | Phase 1 | — |
| BROWSE-01 | (existing) | validated |
| BROWSE-02 | Phase 2 | — |
| BROWSE-03 | (existing) | validated |
| DESK-01 | (existing) | validated |
| DESK-02 | (existing) | validated |
| DESK-03 | Phase 2 | — |
| FILE-01 | (existing) | validated |
| FILE-02 | (existing) | validated |
| FILE-03 | Phase 2 | — |
| TERM-01 | (existing) | validated |
| TERM-02 | Phase 2 | — |
| TERM-03 | Phase 2 | — |
| MEM-01 | Phase 3 | — |
| MEM-02 | Phase 3 | — |
| MEM-03 | Phase 3 | — |
| SCHED-01 | (existing) | validated |
| SCHED-02 | Phase 5 | — |
| REL-01 | Phase 1, 6 | — |
| REL-02 | Phase 1, 4 | — |
| REL-03 | Phase 4 | — |
| WEB-01 | Phase 5 | — |
| WEB-02 | Phase 5 | — |
| WEB-03 | Phase 5 | — |
| CFG-01 | Phase 6 | — |

---
*Last updated: 2026-04-05 after initialization*
