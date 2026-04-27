from flask import Flask, render_template_string, request, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import os
import json
import hashlib

app = Flask(__name__)
app.secret_key = 'chatic-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

USERS_FILE = 'users.json'
MESSAGES_FILE = 'messages.json'
ROOMS_FILE = 'rooms.json'

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {
        'MrAizex': {
            'password': hashlib.sha256('admin123'.encode()).hexdigest(),
            'role': 'owner',
            'avatar': '👑',
            'banned': False
        },
        'dimooon': {
            'password': hashlib.sha256('1111'.encode()).hexdigest(),
            'role': 'admin',
            'avatar': '😎',
            'banned': False
        }
    }

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

def load_messages():
    if os.path.exists(MESSAGES_FILE):
        with open(MESSAGES_FILE, 'r') as f:
            return json.load(f)
    return {'Общая': [], 'Случайная': [], 'Помощь': []}

def save_messages(messages):
    with open(MESSAGES_FILE, 'w') as f:
        json.dump(messages, f)

def load_rooms():
    if os.path.exists(ROOMS_FILE):
        with open(ROOMS_FILE, 'r') as f:
            return json.load(f)
    return ['Общая', 'Случайная', 'Помощь']

users = load_users()
messages = load_messages()
rooms = load_rooms()

# Минимальный шаблон чата
CHAT = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Чатик</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: system-ui; background: #1e1b4b; height: 100vh; display: flex; }
        .sidebar { width: 260px; background: white; padding: 20px; overflow-y: auto; }
        .chat { flex: 1; display: flex; flex-direction: column; background: #f9fafb; }
        .header { padding: 16px; background: white; border-bottom: 1px solid #ddd; }
        .messages { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 8px; }
        .message { display: flex; gap: 8px; align-items: start; }
        .message-own { justify-content: flex-end; }
        .content { background: #e5e7eb; padding: 8px 12px; border-radius: 16px; max-width: 60%; }
        .message-own .content { background: #4f46e5; color: white; }
        .name { font-weight: 600; font-size: 12px; margin-bottom: 4px; }
        .time { font-size: 10px; opacity: 0.7; margin-left: 8px; }
        .input-area { display: flex; gap: 8px; padding: 16px; background: white; border-top: 1px solid #ddd; }
        .input-area input { flex: 1; padding: 12px; border: 1px solid #ddd; border-radius: 24px; outline: none; }
        .input-area button { background: #4f46e5; color: white; border: none; border-radius: 50%; width: 48px; cursor: pointer; }
        .room { padding: 8px; border-radius: 8px; cursor: pointer; margin-bottom: 4px; }
        .room.active { background: #4f46e5; color: white; }
        .user { padding: 8px; border-radius: 8px; cursor: pointer; }
        .user:hover { background: #e5e7eb; }
    </style>
</head>
<body>
<div class="sidebar">
    <div style="text-align:center; margin-bottom:20px;">
        <div style="font-size:48px;">{{ avatar }}</div>
        <div><strong>{{ username }}</strong> ({{ role }})</div>
    </div>
    <div><strong>🏠 Комнаты</strong></div>
    <div id="roomsList"></div>
    <div style="margin-top:20px;"><strong>👥 Пользователи</strong></div>
    <div id="usersList"></div>
    <div style="margin-top:20px;"><a href="/logout">🚪 Выйти</a></div>
</div>
<div class="chat">
    <div class="header"><strong><span id="currentRoom">Общая</span></strong></div>
    <div id="messages" class="messages"></div>
    <div class="input-area">
        <input type="text" id="messageInput" placeholder="Сообщение...">
        <button id="sendBtn">📤</button>
    </div>
</div>
<script>
    let socket = io();
    let currentRoom = 'Общая';
    let username = '{{ username }}';
    
    const messagesDiv = document.getElementById('messages');
    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    
    function addMessage(name, text, time, isOwn) {
        const div = document.createElement('div');
        div.className = `message ${isOwn ? 'message-own' : ''}`;
        div.innerHTML = `<div class="content"><div class="name">${escapeHtml(name)}<span class="time">${time}</span></div><div>${escapeHtml(text)}</div></div>`;
        messagesDiv.appendChild(div);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    
    function addSystemMessage(text) {
        const div = document.createElement('div');
        div.className = 'message';
        div.style.textAlign = 'center';
        div.style.fontSize = '12px';
        div.style.color = '#6b7280';
        div.textContent = text;
        messagesDiv.appendChild(div);
    }
    
    function escapeHtml(str) {
        return str.replace(/[&<>]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;'})[m]);
    }
    
    socket.emit('join', { room: currentRoom });
    
    socket.on('history', (history) => {
        messagesDiv.innerHTML = '';
        history.forEach(msg => addMessage(msg.name, msg.text, msg.time, msg.name === username));
    });
    
    socket.on('message', (msg) => {
        addMessage(msg.name, msg.text, msg.time, msg.name === username);
    });
    
    socket.on('system', addSystemMessage);
    
    socket.on('rooms_list', (rooms) => {
        const container = document.getElementById('roomsList');
        container.innerHTML = rooms.map(r => `<div class="room ${r === currentRoom ? 'active' : ''}" data-room="${r}">📌 ${escapeHtml(r)}</div>`).join('');
        document.querySelectorAll('.room').forEach(el => {
            el.onclick = () => {
                const newRoom = el.dataset.room;
                if(newRoom === currentRoom) return;
                socket.emit('switch_room', { old_room: currentRoom, new_room: newRoom });
                currentRoom = newRoom;
                document.getElementById('currentRoom').textContent = currentRoom;
                document.querySelectorAll('.room').forEach(i => i.classList.remove('active'));
                el.classList.add('active');
                messagesDiv.innerHTML = '<div class="message" style="text-align:center;">⏳ Загрузка...</div>';
            };
        });
    });
    
    socket.on('users_list', (users) => {
        const container = document.getElementById('usersList');
        container.innerHTML = users.map(u => `<div class="user" onclick="alert('Личные сообщения в разработке')">${u.avatar || '👤'} ${escapeHtml(u.name)}</div>`).join('');
    });
    
    sendBtn.onclick = () => {
        if(messageInput.value.trim()) {
            socket.emit('message', { text: messageInput.value, room: currentRoom });
            messageInput.value = '';
        }
    };
    
    messageInput.onkeypress = (e) => { if(e.key === 'Enter') sendBtn.click(); };
    
    socket.emit('get_rooms');
    socket.emit('get_users');
</script>
</body>
</html>'''

LOGIN_PAGE = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Вход</title><style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:linear-gradient(135deg,#1e1b4b,#4c1d95);min-height:100vh;display:flex;align-items:center;justify-content:center}.card{background:white;border-radius:48px;padding:48px;max-width:400px;width:100%}h1{text-align:center;margin-bottom:32px}input{width:100%;padding:16px;border:2px solid #e5e7eb;border-radius:32px;margin-bottom:16px}button{width:100%;padding:16px;background:#4f46e5;color:white;border:none;border-radius:32px;cursor:pointer}.error{background:#fee2e2;color:#dc2626;padding:12px;border-radius:24px;margin-bottom:20px}.footer{text-align:center;margin-top:24px}a{color:#4f46e5}
</style></head>
<body><div class="card"><h1>💬 Чатик</h1>{% if error %}<div class="error">{{ error }}</div>{% endif %}<form method="post"><input type="text" name="username" placeholder="Имя" required autofocus><input type="password" name="password" placeholder="Пароль" required><button type="submit">Войти</button></form><div class="footer">Нет аккаунта? <a href="/register">Регистрация</a></div></div></body>
</html>'''

REGISTER_PAGE = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Регистрация</title><style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:linear-gradient(135deg,#1e1b4b,#4c1d95);min-height:100vh;display:flex;align-items:center;justify-content:center}.card{background:white;border-radius:48px;padding:48px;max-width:400px;width:100%}h1{text-align:center;margin-bottom:32px}input{width:100%;padding:16px;border:2px solid #e5e7eb;border-radius:32px;margin-bottom:16px}button{width:100%;padding:16px;background:#4f46e5;color:white;border:none;border-radius:32px;cursor:pointer}.error{background:#fee2e2;color:#dc2626;padding:12px;border-radius:24px;margin-bottom:20px}.footer{text-align:center;margin-top:24px}a{color:#4f46e5}
</style></head>
<body><div class="card"><h1>📝 Регистрация</h1>{% if error %}<div class="error">{{ error }}</div>{% endif %}<form method="post"><input type="text" name="username" placeholder="Имя (3-20 символов)" required autofocus><input type="password" name="password" placeholder="Пароль (мин. 4)" required><button type="submit">Зарегистрироваться</button></form><div class="footer">Уже есть аккаунт? <a href="/login">Войти</a></div></div></body>
</html>'''

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    user = users.get(session['username'])
    if not user or user.get('banned'):
        session.clear()
        return redirect(url_for('login'))
    role_display = {'owner': 'Владелец', 'admin': 'Админ', 'moderator': 'Модер', 'user': 'Пользователь'}.get(user['role'], 'Пользователь')
    return render_template_string(CHAT, username=session['username'], role=role_display, avatar=user.get('avatar', '👤'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed = hashlib.sha256(password.encode()).hexdigest()
        if username in users and users[username]['password'] == hashed:
            if users[username].get('banned'):
                return render_template_string(LOGIN_PAGE, error='Вы заблокированы')
            session['username'] = username
            return redirect(url_for('index'))
        return render_template_string(LOGIN_PAGE, error='Неверное имя или пароль')
    return render_template_string(LOGIN_PAGE, error=None)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users:
            return render_template_string(REGISTER_PAGE, error='Пользователь уже существует')
        if len(username) < 3 or len(username) > 20:
            return render_template_string(REGISTER_PAGE, error='Имя от 3 до 20 символов')
        if len(password) < 4:
            return render_template_string(REGISTER_PAGE, error='Пароль мин. 4 символа')
        users[username] = {'password': hashlib.sha256(password.encode()).hexdigest(), 'role': 'user', 'avatar': '👤', 'banned': False}
        save_users(users)
        return redirect(url_for('login'))
    return render_template_string(REGISTER_PAGE, error=None)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@socketio.on('join')
def handle_join(data):
    username = session.get('username')
    if not username or users.get(username, {}).get('banned'):
        return
    room = data['room']
    join_room(room)
    emit('history', messages.get(room, []), to=request.sid)

@socketio.on('message')
def handle_message(data):
    username = session.get('username')
    if not username or users.get(username, {}).get('banned'):
        return
    room = data['room']
    text = data['text']
    message = {'name': username, 'text': text, 'time': datetime.now().strftime('%H:%M:%S'), 'role': users[username]['role']}
    messages.setdefault(room, []).append(message)
    save_messages(messages)
    emit('message', message, to=room, broadcast=True)

@socketio.on('switch_room')
def handle_switch_room(data):
    username = session.get('username')
    if not username:
        return
    old_room = data['old_room']
    new_room = data['new_room']
    leave_room(old_room)
    join_room(new_room)
    emit('history', messages.get(new_room, []), to=request.sid)

@socketio.on('get_rooms')
def handle_get_rooms():
    emit('rooms_list', rooms)

@socketio.on('get_users')
def handle_get_users():
    users_list = [{'name': name, 'role': data['role'], 'avatar': data.get('avatar', '👤')} for name, data in users.items() if not data.get('banned')]
    emit('users_list', users_list)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
