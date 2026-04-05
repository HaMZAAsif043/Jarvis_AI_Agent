# Requirements

## v1 Requirements

### Autonomy (Core Engine)
- [ ] **AUTO-01**: JARVIS can accept natural language commands via web dashboard or CLI and execute them end-to-end without human intervention
- [ ] **AUTO-02**: JARVIS can chain multiple tool calls together to complete complex multi-step tasks (e.g., "find my invoices, read them, and email totals")
- [ ] **AUTO-03**: JARVIS decomposes complex requests into step-by-step plans before execution

### Browser Control
- [ ] **BROWSE-01**: JARVIS can navigate to URLs, click elements, fill forms, extract text/data from pages
- [ ] **BROWSE-02**: JARVIS can handle authentication flows and session management in browser
- [ ] **BROWSE-03**: JARVIS can take screenshots and return page content as structured data

### Desktop Control
- [ ] **DESK-01**: JARVIS can list, focus, open, and close application windows
- [ ] **DESK-02**: JARVIS can simulate mouse clicks, movements, and keyboard input to interact with any application
- [ ] **DESK-03**: JARVIS can capture screenshots and identify UI elements for interaction

### File Management
- [ ] **FILE-01**: JARVIS can search for files by name, extension, or content across specified drives
- [ ] **FILE-02**: JARVIS can create, read, edit, copy, move, and delete files and directories
- [ ] **FILE-03**: JARVIS can filter files by type (PDF, DOCX, XLSX, images, etc.) and extract metadata

### Terminal Execution
- [ ] **TERM-01**: JARVIS can execute shell/PowerShell commands and return output
- [ ] **TERM-02**: JARVIS can run Python scripts and manage virtual environments
- [ ] **TERM-03**: JARVIS can manage processes (start, stop, list running)

### Memory & Context
- [ ] **MEM-01**: JARVIS persists user preferences, learned patterns, and important information across sessions
- [ ] **MEM-02**: JARVIS maintains conversation context within a session for multi-step task coherence
- [ ] **MEM-03**: JARVIS can recall and reference previous tasks when asked (e.g., "do what you did yesterday")

### Task Scheduling
- [ ] **SCHED-01**: JARVIS can schedule recurring or one-time automated tasks (e.g., "check email daily at 9 AM")
- [ ] **SCHED-02**: Scheduled tasks persist across restarts and can be listed/modified/deleted

### Reliability & Feedback
- [ ] **REL-01**: JARVIS provides clear execution reports: what was attempted, what succeeded, what failed
- [ ] **REL-02**: JARVIS handles errors gracefully — retries failed operations, falls back to alternatives, or asks for clarification
- [ ] **REL-03**: JARVIS confirms destructive actions (file deletion, process kill) before proceeding

### Web Dashboard
- [ ] **WEB-01**: Web UI for sending commands, viewing execution status, and seeing results in real-time
- [ ] **WEB-02**: Web UI shows execution history and past task results
- [ ] **WEB-03**: Web UI for managing scheduled tasks

### Configuration
- [ ] **CFG-01**: Simple env-based config for Gemini API key and server settings

## v2 Requirements (Deferred)
- Voice input/output
- Multi-PC coordination
- Integration with email APIs (SendGrid, Gmail API)
- Slack/Discord bot interface
- Custom tool plugin system

## Out of Scope
- Mobile device control — desktop/Windows only for now
- Multi-user support — single-user system
- Cloud deployment — runs locally only

## Traceability

| Req ID | Phase | Status |
|--------|-------|--------|
| AUTO-01 | 1, 4 | — |
| AUTO-02 | 1 | — |
| AUTO-03 | 1 | — |
| BROWSE-01 | (existing) | validated |
| BROWSE-02 | 2 | — |
| BROWSE-03 | (existing) | validated |
| DESK-01 | (existing) | validated |
| DESK-02 | (existing) | validated |
| DESK-03 | 2 | — |
| FILE-01 | (existing) | validated |
| FILE-02 | (existing) | validated |
| FILE-03 | 2 | — |
| TERM-01 | (existing) | validated |
| TERM-02 | 2 | — |
| TERM-03 | 2 | — |
| MEM-01 | 3 | — |
| MEM-02 | 3 | — |
| MEM-03 | 3 | — |
| SCHED-01 | (existing) | validated |
| SCHED-02 | 5 | — |
| REL-01 | 1, 6 | — |
| REL-02 | 1, 4 | — |
| REL-03 | 4 | — |
| WEB-01 | 5 | — |
| WEB-02 | 5 | — |
| WEB-03 | 5 | — |
| CFG-01 | 6 | — |

---
*Last updated: 2026-04-05 after initialization*
