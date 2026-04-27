from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import os
import json

app = Flask(__name__)
app.secret_key = 'secret-key-change-this'
socketio = SocketIO(app, cors_allowed_origins="*")

# Файлы для хранения данных
USERS_FILE = 'users.json'
MESSAGES_FILE = 'messages.json'

# Загрузка пользователей
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {'admin': {'password': 'admin123', 'role': 'admin'}}  # admin/admin123

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

# Загрузка сообщений
def load_messages():
    if os.path.exists(MESSAGES_FILE):
        with open(MESSAGES_FILE, 'r') as f:
            return json.load(f)
    return {'Общая': [], 'Случайная': [], 'Помощь': []}

def save_messages(messages):
    with open(MESSAGES_FILE, 'w') as f:
        json.dump(messages, f)

users = load_users()
history = load_messages()
MAX_HISTORY = 100

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'], role=session.get('role', 'user'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username]['password'] == password:
            session['username'] = username
            session['role'] = users[username]['role']
            return redirect(url_for('index'))
        return 'Неверное имя или пароль', 401
    return '''
        <form method="post">
            <input name="username" placeholder="Имя">
            <input name="password" type="password" placeholder="Пароль">
            <button>Войти</button>
        </form>
        <a href="/register">Регистрация</a>
    '''

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users:
            return 'Пользователь уже существует', 400
        users[username] = {'password': password, 'role': 'user'}
        save_users(users)
        return redirect(url_for('login'))
    return '''
        <form method="post">
            <input name="username" placeholder="Имя">
            <input name="password" type="password" placeholder="Пароль">
            <button>Зарегистрироваться</button>
        </form>
    '''

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@socketio.on('join')
def handle_join(data):
    room = data['room']
    join_room(room)
    emit('history', history.get(room, []), to=request.sid)
    emit('system', f'{session["username"]} присоединился', to=room, broadcast=True)

@socketio.on('message')
def handle_message(data):
    username = session['username']
    role = session.get('role', 'user')
    text = data['text']
    room = data['room']
    time_str = datetime.now().strftime('%H:%M:%S')
    msg_id = str(int(datetime.now().timestamp() * 1000))
    message = {'id': msg_id, 'name': username, 'text': text, 'time': time_str, 'role': role, 'deleted': False}
    
    history.setdefault(room, []).append(message)
    if len(history[room]) > MAX_HISTORY:
        history[room] = history[room][-MAX_HISTORY:]
    save_messages(history)
    emit('message', message, to=room, broadcast=True)

@socketio.on('delete_message')
def handle_delete(data):
    username = session['username']
    role = session.get('role', 'user')
    msg_id = data['messageId']
    room = data['room']
    
    for msg in history.get(room, []):
        if msg.get('id') == msg_id:
            if role == 'admin' or msg.get('name') == username:
                msg['deleted'] = True
                msg['text'] = '[Сообщение удалено]'
                save_messages(history)
                emit('message_update', {'id': msg_id, 'text': '[Сообщение удалено]', 'deleted': True}, to=room, broadcast=True)
            break

@socketio.on('switch_room')
def handle_switch_room(data):
    old_room = data['old_room']
    new_room = data['new_room']
    leave_room(old_room)
    join_room(new_room)
    emit('history', history.get(new_room, []), to=request.sid)

@socketio.on('get_users')
def handle_get_users():
    emit('users_list', [{'name': u, 'role': users[u]['role']} for u in users])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
