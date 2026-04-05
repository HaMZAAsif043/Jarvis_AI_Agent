"""Entry point for `python -m jarvis`."""
import asyncio
import sys

from jarvis.main import run_cli, run_server


if __name__ == "__main__":
    if "--cli" in sys.argv:
        asyncio.run(run_cli())
    else:
        import jarvis.config as cfg
        if not cfg.GEMINI_API_KEY:
            print("ERROR: GEMINI_API_KEY is not set. Set it in .env file.")
            sys.exit(1)
        print(f"Starting JARVIS web dashboard at http://{cfg.HOST}:{cfg.PORT}")
        asyncio.run(run_server())
