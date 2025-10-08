import asyncio
import json
import os
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

# Load questions from JSON file
def load_questions():
    """Load questions from questions.json file"""
    questions_file = os.path.join(os.path.dirname(__file__), 'questions.json')
    try:
        with open(questions_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('questions', [])
    except FileNotFoundError:
        print(f"Warning: questions.json not found at {questions_file}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing questions.json: {e}")
        return []

def get_current_question():
    """Get the current question based on game state"""
    questions = load_questions()
    if not questions:
        # Fallback to default question if no questions loaded
        return {
            'question': 'Name something you take on vacation',
            'answers': [
                {'id': 1, 'text': 'Toothbrush', 'points': 30, 'revealed': False},
                {'id': 2, 'text': 'Sunscreen', 'points': 25, 'revealed': False},
                {'id': 3, 'text': 'Passport', 'points': 20, 'revealed': False},
                {'id': 4, 'text': 'Camera', 'points': 15, 'revealed': False},
                {'id': 5, 'text': 'Clothes', 'points': 10, 'revealed': False},
            ]
        }
    
    # For now, use the first question. Later we can add question selection logic
    current_q = questions[0]
    return {
        'question': current_q['question'],
        'answers': [
            {**answer, 'revealed': False} for answer in current_q['answers']
        ]
    }

# Initialize game state with loaded question
current_question_data = get_current_question()
questions = load_questions()
initial_question_id = questions[0]['id'] if questions else 1

game_state = {
    'question': current_question_data['question'],
    'answers': current_question_data['answers'],
    'last_selected': None,
    'strikes': 0,
    'roundScore': 0,
    'current_question_id': initial_question_id,
}

# Team info (displayed on play/judge pages)
game_state.update({
    'team1Name': 'Team 1',
    'team2Name': 'Team 2',
    'team1Score': 0,
    'team2Score': 0,
    'activeTeam': 1,
})

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
            if not a.get('revealed'):
                a['revealed'] = True
                # add points to round score
                game_state['roundScore'] = game_state.get('roundScore', 0) + a.get('points', 0)
                game_state['last_selected'] = a
                await broadcast_state()
                return {'ok': True, 'selected': a, 'roundScore': game_state['roundScore']}
            else:
                return {'ok': True, 'selected': a, 'roundScore': game_state.get('roundScore', 0)}
    return JSONResponse({'error': 'not found'}, status_code=status.HTTP_404_NOT_FOUND)


@app.post('/api/reset')
async def api_reset():
    for a in game_state['answers']:
        a['revealed'] = False
    game_state['last_selected'] = None
    # reset round score on next round
    game_state['roundScore'] = 0
    await broadcast_state()
    return {'ok': True}


@app.post('/api/new_question')
async def api_new_question(payload: dict = None):
    """Load a new question from the JSON file"""
    question_id = payload.get('question_id') if payload else None
    questions = load_questions()
    
    if not questions:
        return JSONResponse({'error': 'No questions available'}, status_code=status.HTTP_404_NOT_FOUND)
    
    # If question_id is specified, find that specific question
    if question_id is not None:
        selected_question = next((q for q in questions if q['id'] == question_id), None)
        if not selected_question:
            return JSONResponse({'error': f'Question with id {question_id} not found'}, status_code=status.HTTP_404_NOT_FOUND)
    else:
        # For now, just cycle through questions. Later we can add random selection
        current_id = game_state.get('current_question_id', 0)
        next_id = (current_id % len(questions)) + 1
        selected_question = next((q for q in questions if q['id'] == next_id), questions[0])
    
    # Update game state with new question
    game_state['question'] = selected_question['question']
    game_state['answers'] = [
        {**answer, 'revealed': False} for answer in selected_question['answers']
    ]
    game_state['last_selected'] = None
    game_state['roundScore'] = 0
    game_state['strikes'] = 0
    game_state['current_question_id'] = selected_question['id']
    
    await broadcast_state()
    return {'ok': True, 'question_id': selected_question['id']}


@app.post('/api/next_round')
async def api_next_round():
    """Start the next round: award current points, load new question, reset round state"""
    # First, award any current round score to the active team
    current_round_score = game_state.get('roundScore', 0)
    if current_round_score > 0:
        if game_state.get('activeTeam', 1) == 1:
            game_state['team1Score'] = game_state.get('team1Score', 0) + current_round_score
        else:
            game_state['team2Score'] = game_state.get('team2Score', 0) + current_round_score
    
    # Load a new question
    questions = load_questions()
    if not questions:
        return JSONResponse({'error': 'No questions available'}, status_code=status.HTTP_404_NOT_FOUND)
    
    # Cycle to the next question
    current_id = game_state.get('current_question_id', 0)
    next_id = (current_id % len(questions)) + 1
    selected_question = next((q for q in questions if q['id'] == next_id), questions[0])
    
    # Update game state with new question and reset round state
    game_state['question'] = selected_question['question']
    game_state['answers'] = [
        {**answer, 'revealed': False} for answer in selected_question['answers']
    ]
    game_state['last_selected'] = None
    game_state['roundScore'] = 0
    game_state['strikes'] = 0
    game_state['current_question_id'] = selected_question['id']
    
    await broadcast_state()
    return {
        'ok': True, 
        'question_id': selected_question['id'],
        'awarded_points': current_round_score,
        'team1Score': game_state.get('team1Score', 0),
        'team2Score': game_state.get('team2Score', 0)
    }


@app.get('/api/questions')
async def api_get_questions():
    """Get list of all available questions"""
    questions = load_questions()
    return {
        'questions': [
            {
                'id': q['id'],
                'question': q['question'],
                'answer_count': len(q['answers'])
            } for q in questions
        ]
    }


@app.post('/api/active')
async def api_set_active(payload: dict):
    team = payload.get('team')
    if team not in (1, 2):
        return JSONResponse({'error': 'team must be 1 or 2'}, status_code=status.HTTP_400_BAD_REQUEST)
    game_state['activeTeam'] = team
    await broadcast_state()
    return {'ok': True, 'active': team}


@app.post('/api/award')
async def api_award():
    # award roundScore to active team and reset roundScore
    pts = game_state.get('roundScore', 0)
    if pts <= 0:
        return {'ok': True, 'awarded': 0}
    if game_state.get('activeTeam', 1) == 1:
        game_state['team1Score'] = game_state.get('team1Score', 0) + pts
    else:
        game_state['team2Score'] = game_state.get('team2Score', 0) + pts
    game_state['roundScore'] = 0
    await broadcast_state()
    return {'ok': True, 'awarded': pts}


@app.post('/api/award_steal')
async def api_award_steal():
    # award roundScore to the non-active team (steal) and reset roundScore
    pts = game_state.get('roundScore', 0)
    if pts <= 0:
        return {'ok': True, 'awarded': 0}
    other = 2 if game_state.get('activeTeam', 1) == 1 else 1
    if other == 1:
        game_state['team1Score'] = game_state.get('team1Score', 0) + pts
    else:
        game_state['team2Score'] = game_state.get('team2Score', 0) + pts
    game_state['roundScore'] = 0
    await broadcast_state()
    return {'ok': True, 'awarded': pts, 'to': other}


@app.post('/api/strike')
async def api_add_strike():
    # increment strikes up to 3
    current = game_state.get('strikes', 0)
    if current < 3:
        game_state['strikes'] = current + 1
        await broadcast_state()
    return {'ok': True, 'strikes': game_state.get('strikes', 0)}


@app.post('/api/clear_strikes')
async def api_clear_strikes():
    game_state['strikes'] = 0
    await broadcast_state()
    return {'ok': True, 'strikes': 0}


@sio.event(namespace='/game')
async def connect(sid, environ):
    # send the initial state to the connected client
    await sio.emit('state_update', game_state, room=sid, namespace='/game')


asgi_app = socketio.ASGIApp(sio, other_asgi_app=app)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:asgi_app', host='0.0.0.0', port=8000, reload=True)
