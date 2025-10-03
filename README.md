# Family Feud Flask App

Simple Flask app that serves two pages:

- `/` - Player/audience view (shows question and revealed answers)
- `/judge` - Judge view (shows all answers; clicking an answer selects/reveals it)

Server pushes updates via Socket.IO (namespace `/game`).

Quick start:

1. Create a venv and install requirements:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the server.

Option A (easy, no eventlet): run the app directly using the threading async mode. This avoids eventlet and the monkey-patch warning:

```bash
python app.py
```

For production, consider running behind an ASGI server (uvicorn or gunicorn with an async worker) and/or using a message queue (Redis) with Flask-SocketIO's message queue feature to scale across processes. Example production approaches:

Option B (FastAPI + python-socketio ASGI app):

Development (auto-reload):

```bash
uvicorn main:asgi_app --reload --host 0.0.0.0 --port 8000
```

Production (example with Gunicorn + Uvicorn workers):

```bash
gunicorn -k uvicorn.workers.UvicornWorker main:asgi_app -w 4
```

3. Open http://localhost:5000 and http://localhost:5000/judge
