# JARVIS AI - Setup Guide

## 1. Set your Gemini API key

Create a `.env` file next to `config.py`:

```
GEMINI_API_KEY=your_api_key_here
```

Get a key free at: https://aistudio.google.com/apikey

Optional env vars:

```
GEMINI_MODEL=gemini-2.0-flash       # Model to use (default)
JARVIS_HOST=127.0.0.1              # Server host (default)
JARVIS_PORT=8000                   # Server port (default)
```

## 2. Install Playwright browsers (first time only)

```bash
cd C:\Users\MADIHA\Desktop\leads_automation
.venv\Scripts\python.exe -m playwright install chromium
```

This downloads a headless Chromium browser (~100MB). Only needed if you want browser automation.

## 3. Run the web dashboard

```bash
cd C:\Users\MADIHA\Desktop\leads_automation
.venv\Scripts\activate
python -m jarvis.main
```

Then open: http://127.0.0.1:8000

## 4. Run in CLI mode (testing)

```bash
python -m jarvis.main --cli
```

## 5. Examples of what to ask

- "Search my Desktop for all PDF files."
- "Take a screenshot of my screen."
- "List all open windows on my PC."
- "Open google.com and get the page text."
- "What's the current time?"  (chat mode)
- "Create a text file at C:\temp\notes.txt with hello world."

## Architecture

```
User (Web/CLI) → Gemini Brain (plan) → Tool Router (exec) → Tools → Stream results back
```
