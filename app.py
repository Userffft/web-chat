from flask import Flask, render_template
from flask_socketio import SocketIO, send, emit, join_room, leave_room
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Хранилище сообщений
history = {
    'Общая': [],
    'Случайная': [],
    'Помощь': []
}
MAX_HISTORY = 100

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join')
def handle_join(data):
    name = data['name']
    room = data['room']
    join_room(room)
    emit('history', history[room], to=request.sid)
    send(f'{name} присоединился к чату', to=room, broadcast=True)

@socketio.on('message')
def handle_message(data):
    name = data['name']
    text = data['text']
    room = data['room']
    time_str = datetime.now().strftime('%H:%M:%S')
    message = {'name': name, 'text': text, 'time': time_str}
    
    history[room].append(message)
    if len(history[room]) > MAX_HISTORY:
        history[room] = history[room][-MAX_HISTORY:]
    
    emit('message', message, to=room, broadcast=True)

@socketio.on('switch_room')
def handle_switch_room(data):
    name = data['name']
    old_room = data['old_room']
    new_room = data['new_room']
    leave_room(old_room)
    join_room(new_room)
    emit('history', history[new_room], to=request.sid)
    send(f'{name} перешёл в комнату {new_room}', to=new_room, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8080, debug=True)