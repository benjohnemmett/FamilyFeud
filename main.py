import asyncio
from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import socketio

# Async Socket.IO server and FastAPI app
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()
templates = Jinja2Templates(directory='templates')

# Serve static files (CSS/JS/assets)
app.mount("/static", StaticFiles(directory="static"), name="static")

# In-memory game state
game_state = {
    'question': 'Name something you take on vacation',
    'answers': [
        {'id': 1, 'text': 'Toothbrush', 'points': 30, 'revealed': False},
        {'id': 2, 'text': 'Sunscreen', 'points': 25, 'revealed': False},
        {'id': 3, 'text': 'Passport', 'points': 20, 'revealed': False},
        {'id': 4, 'text': 'Camera', 'points': 15, 'revealed': False},
        {'id': 5, 'text': 'Clothes', 'points': 10, 'revealed': False},
    ],
    'last_selected': None,
}

async def broadcast_state():
    # schedule emit to avoid awaiting in non-async contexts
    await sio.emit('state_update', game_state, namespace='/game')


@app.get('/', response_class=HTMLResponse)
async def play(request: Request):
    return templates.TemplateResponse('play.html', {'request': request})


@app.get('/judge', response_class=HTMLResponse)
async def judge(request: Request):
    return templates.TemplateResponse('judge.html', {'request': request})


@app.get('/api/state')
async def api_state():
    return game_state


@app.post('/api/select')
async def api_select(payload: dict):
    answer_id = payload.get('id')
    if answer_id is None:
        return JSONResponse({'error': 'id required'}, status_code=status.HTTP_400_BAD_REQUEST)
    for a in game_state['answers']:
        if a['id'] == answer_id:
            a['revealed'] = True
            game_state['last_selected'] = a
            await broadcast_state()
            return {'ok': True, 'selected': a}
    return JSONResponse({'error': 'not found'}, status_code=status.HTTP_404_NOT_FOUND)


@app.post('/api/reset')
async def api_reset():
    for a in game_state['answers']:
        a['revealed'] = False
    game_state['last_selected'] = None
    await broadcast_state()
    return {'ok': True}


@sio.event(namespace='/game')
async def connect(sid, environ):
    # send the initial state to the connected client
    await sio.emit('state_update', game_state, room=sid, namespace='/game')


asgi_app = socketio.ASGIApp(sio, other_asgi_app=app)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:asgi_app', host='0.0.0.0', port=8000, reload=True)
