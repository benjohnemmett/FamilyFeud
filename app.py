from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev'
# Use the threading async mode by default to avoid requiring eventlet.
# If you want to run with eventlet for better websocket performance, use run.py
socketio = SocketIO(app, async_mode='threading')

# In-memory game state. For a real app, persist this.
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

def broadcast_state():
    socketio.emit('state_update', game_state, namespace='/game')

@app.route('/')
def play():
    return render_template('play.html')

@app.route('/judge')
def judge():
    return render_template('judge.html')

@app.route('/api/state')
def api_state():
    return jsonify(game_state)

@app.route('/api/select', methods=['POST'])
def api_select():
    data = request.get_json() or {}
    answer_id = data.get('id')
    if answer_id is None:
        return jsonify({'error': 'id required'}), 400
    for a in game_state['answers']:
        if a['id'] == answer_id:
            a['revealed'] = True
            game_state['last_selected'] = a
            broadcast_state()
            return jsonify({'ok': True, 'selected': a})
    return jsonify({'error': 'not found'}), 404

@app.route('/api/reset', methods=['POST'])
def api_reset():
    for a in game_state['answers']:
        a['revealed'] = False
    game_state['last_selected'] = None
    broadcast_state()
    return jsonify({'ok': True})

@socketio.on('connect', namespace='/game')
def on_connect():
    emit('state_update', game_state)


if __name__ == '__main__':
    # Run using the Werkzeug development server with threading-based Socket.IO
    socketio.run(app, host='0.0.0.0', port=5000)


