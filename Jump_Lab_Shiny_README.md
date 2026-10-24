# Jump Lab AI — Shiny for Python project

This package keeps the original HTML/JavaScript game and adds a Python AI endpoint. It uses the Shiny for Python framework with a lightweight ASGI wrapper so the game can be served at `/game/` and the backend at `/api/suggest`.

## Local test (instructor only)

1. Install Python 3.10+.
2. In this folder: `python3 -m pip install -r requirements.txt`
3. Start: `python3 -m uvicorn app:app --host 127.0.0.1 --port 8000`
4. Visit `http://127.0.0.1:8000/game/` in Chrome.
5. Offline practice works without an API key. For live AI, set the `OPENAI_API_KEY` environment variable **on the server** (never in HTML). Example: `export OPENAI_API_KEY='your-new-key'` before starting the server.

## Publishing

This is an ASGI application with a Shiny sub-application. **Check that your chosen Shiny hosting provider supports custom ASGI entrypoints and routes** before deploying; a service that accepts only conventional `shiny run app.py` apps may require adaptation. A general Python ASGI host can run it with `uvicorn app:app --host 0.0.0.0 --port $PORT`. Hosting is not configured or tested here. Do not put your key in git or upload it with the ZIP. HTTPS is required for public deployment.

## Workshop readiness

- Students use a single link `/game/`; one game per browser session.
- Live AI changes are strictly limited to validated settings: jump power, gravity, game speed, star points, and theme.
- Basic in-memory IP rate limiting (12/minute) is **prototype-only** and not robust across multiple workers or shared school IPs. Add per-session limits, daily spend limits, logging minimization, abuse protection, and test concurrent load before classroom use.
- No micro:bit integration yet. Keyboard jump works.
- This is an initial prototype, not a completed classroom deployment. Check child privacy requirements and school policy before allowing student prompts to reach OpenAI.
