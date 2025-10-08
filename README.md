# Family Feud — FastAPI + Socket.IO

This repository is a small real-time Family Feud style app.
It serves two main pages:

- `/` — Player / audience view (show question, revealed answers, round score, strikes)
- `/judge` — Judge view (controls to reveal answers, add strikes, award points, control active team)

Realtime updates use python-socketio (ASGI) with the Socket.IO browser client on the frontend. The server is implemented with FastAPI and an embedded Socket.IO ASGI app.

Requirements
- Python 3.10+
- Install packages in `requirements.txt` (fastapi, python-socketio, uvicorn, jinja2, etc.)

Quick start (development)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Option 1: Run with uvicorn directly**
```bash
uvicorn main:asgi_app --reload --host 127.0.0.1 --port 8000
```

**Option 2: Run main.py directly (recommended for development)**
```bash
python main.py
```

Open the pages in your browser:
- Player/audience: http://127.0.0.1:8000/
- Judge controls:   http://127.0.0.1:8000/judge

Server API (useful for automation/testing)
- GET `/api/state` — returns current game state JSON
- POST `/api/select` — reveal an answer, body { id: number }
  - When the judge reveals an answer, the server adds that answer's points to `roundScore` and broadcasts the updated state.
- POST `/api/reset` — reset revealed answers and clear `roundScore` (used for Next Round)
- POST `/api/active` — set active team, body { team: 1|2 }
- POST `/api/strike` — increment strikes (up to 3)
- POST `/api/clear_strikes` — clear strikes to 0
- POST `/api/award` — award the current `roundScore` to the active team and reset `roundScore`
- POST `/api/award_steal` — award the current `roundScore` to the non-active team (steal) and reset `roundScore`

Frontend notes
- Shared static assets: `static/app.js` (socket connection + client boot), `static/styles.css`.
- Templates: `templates/play.html` and `templates/judge.html`. Each page defines `window.renderState(state)` to render state updates, and `static/app.js` calls that hook after receiving `state_update` Socket.IO events.

Development tips
- The app keeps state in-memory (`main.py.game_state`). If you restart the server state will reset.
- To persist scores across runs, add a small storage backend (file, sqlite) and update the endpoints.
- For production: run behind a process manager and consider using a message queue (Redis) with python-socketio to scale across processes.

License & contribution
- This is a small personal project. Feel free to open issues/PRs.

