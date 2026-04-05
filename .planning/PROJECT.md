# JARVIS — Autonomous PC Agent

## What This Is

JARVIS is a fully autonomous AI-powered desktop agent that can control your PC and perform any task you ask. It currently has a core architecture (Gemini AI brain, tool router, browser/desktop/file/terminal tools, web dashboard, scheduler) and needs to be completed into a production-ready, fully autonomous system where you give a natural language command and JARVIS figures out how to execute it using the right tools — including full PC control.

## Core Value

When you ask JARVIS to do anything on your PC, it understands the intent, picks the right tools, executes reliably, and reports results — without any manual configuration or intervention.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] **AUTONOMY-01**: JARVIS can accept natural language commands via web dashboard or CLI and execute them end-to-end without human intervention
- [ ] **AUTONOMY-02**: JARVIS can chain multiple tool calls together to complete complex multi-step tasks (e.g., "find my invoices on desktop, read them, and email the totals")
- [ ] **BROWSER-01**: JARVIS can navigate websites, fill forms, click buttons, extract data, and handle authentication flows
- [ ] **DESKTOP-01**: JARVIS can control desktop applications, manage windows, take screenshots, and interact with UI elements via mouse/keyboard
- [ ] **FILES-01**: JARVIS can search for files across drives, organize them, create/edit/delete files, and copy/move between locations
- [ ] **TERMINAL-01**: JARVIS can run shell commands, install packages, manage processes, and return output
- [ ] **MEMORY-01**: JARVIS remembers previous conversations, user preferences, and learned patterns across sessions
- [ ] **MEMORY-02**: JARVIS maintains short-term context within a conversation for coherent multi-step task execution
- [ ] **SCHEDULER-01**: JARVIS can schedule and autonomously execute recurring tasks (e.g., "check my email every morning at 9 AM")
- [ ] **RELIABILITY-01**: JARVIS reports what it did, what succeeded, and what failed with clear explanations
- [ ] **RELIABILITY-02**: JARVIS handles errors gracefully — retries, falls back to alternative approaches, or asks for clarification when stuck
- [ ] **CONFIG-01**: Simple configuration system for API keys, preferences, and tool settings

### Out of Scope

- Mobile device control — desktop/Windows only for now
- Voice I/O — text-based input only (voice can be added later)
- Multi-user support — single-user system

## Context

- **Existing codebase**: `jarvis/` directory with agent brain (Gemini), tool router, browser/desktop/file/terminal tools, long/short-term memory, scheduler, web dashboard, and config
- **AI provider**: Google Gemini (gemini-2.0-flash default) via google-genai SDK
- **Backend**: FastAPI + Uvicorn for web dashboard server
- **Automation stack**: Playwright (browser), PyAutoGUI + PyGetWindow (desktop), APScheduler (task scheduling)
- **Python 3.11** via `.venv` on Windows 11
- **Existing tool modules** are scaffolds — need full implementation and error handling
- The "brain" needs proper planning/reasoning logic to autonomously decompose user requests into tool chains
- Memory system exists but needs persistent storage and retrieval logic

## Constraints

- **[AI Provider]**: Gemini via API — costs money per request — Gemini API key required
- **[Platform]**: Windows 11 only — all tool implementations must work on Windows
- **[Language]**: Python 3.11+ — must work within Python ecosystem
- **[Security]**: Agent runs with user privileges — destructive operations need safeguards (no silent `rm -rf` equivalents)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Gemini over OpenAI/Claude | Free tier available, SETUP.md already configured | — Pending (user confirmation) |
| FastAPI web dashboard over Electron/CLI-only | Web UI is accessible from anywhere, no install overhead | ✓ Good |
| Python ecosystem | User is Python/Django developer | ✓ Good |
| Tool-based architecture | Modular, extensible, testable | ✓ Good |
| Playwright over Selenium | Playwright is more reliable and actively maintained | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-05 after initialization*
