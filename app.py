from flask import Flask, render_template_string, request, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import os
import json

app = Flask(__name__)
app.secret_key = 'supersecretkey123'
socketio = SocketIO(app, cors_allowed_origins="*")

USERS_FILE = 'users.json'
MESSAGES_FILE = 'messages.json'

# Загрузка пользователей
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {'admin': {'password': 'admin123', 'role': 'admin'}}

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

# HTML шаблон прямо в коде
LOGIN_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Чатик · Вход</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .card {
            background: white;
            border-radius: 32px;
            padding: 40px;
            max-width: 400px;
            width: 100%;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
        }
        h1 {
            text-align: center;
            margin-bottom: 32px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        input {
            width: 100%;
            padding: 14px 16px;
            border: 2px solid #e5e7eb;
            border-radius: 24px;
            margin-bottom: 16px;
            font-size: 16px;
            outline: none;
        }
        input:focus {
            border-color: #667eea;
        }
        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 24px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
        }
        .error {
            background: #fee2e2;
            color: #dc2626;
            padding: 10px;
            border-radius: 16px;
            margin-bottom: 16px;
            text-align: center;
        }
        .footer {
            text-align: center;
            margin-top: 24px;
            color: #6b7280;
        }
        a { color: #667eea; text-decoration: none; }
    </style>
</head>
<body>
    <div class="card">
        <h1>💬 Чатик</h1>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="post">
            <input type="text" name="username" placeholder="Имя пользователя" required autofocus>
            <input type="password" name="password" placeholder="Пароль" required>
            <button type="submit">Войти</button>
        </form>
        <div class="footer">
            Нет аккаунта? <a href="/register">Зарегистрироваться</a>
        </div>
    </div>
</body>
</html>
'''

REGISTER_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Чатик · Регистрация</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .card {
            background: white;
            border-radius: 32px;
            padding: 40px;
            max-width: 400px;
            width: 100%;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
        }
        h1 {
            text-align: center;
            margin-bottom: 32px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        input {
            width: 100%;
            padding: 14px 16px;
            border: 2px solid #e5e7eb;
            border-radius: 24px;
            margin-bottom: 16px;
            font-size: 16px;
            outline: none;
        }
        input:focus {
            border-color: #667eea;
        }
        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 24px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
        }
        .error {
            background: #fee2e2;
            color: #dc2626;
            padding: 10px;
            border-radius: 16px;
            margin-bottom: 16px;
            text-align: center;
        }
        .footer {
            text-align: center;
            margin-top: 24px;
            color: #6b7280;
        }
        a { color: #667eea; text-decoration: none; }
    </style>
</head>
<body>
    <div class="card">
        <h1>📝 Регистрация</h1>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="post">
            <input type="text" name="username" placeholder="Имя (мин. 3 символа)" required autofocus>
            <input type="password" name="password" placeholder="Пароль (мин. 4 символа)" required>
            <button type="submit">Зарегистрироваться</button>
        </form>
        <div class="footer">
            Уже есть аккаунт? <a href="/login">Войти</a>
        </div>
    </div>
</body>
</html>
'''

CHAT_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Чатик</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .chat-container { max-width: 1200px; margin: 0 auto; }
        .chat-card {
            background: white;
            border-radius: 32px;
            overflow: hidden;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
        }
        .header {
            background: linear-gradient(135deg, #4f46e5, #7c3aed);
            padding: 20px 24px;
            color: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .main { display: flex; height: 550px; }
        .sidebar {
            width: 260px;
            background: #f9fafb;
            border-right: 1px solid #e5e7eb;
            padding: 16px;
            overflow-y: auto;
        }
        .sidebar-title {
            font-weight: 600;
            margin-bottom: 12px;
            color: #374151;
        }
        .user-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px;
            border-radius: 8px;
            margin-bottom: 4px;
        }
        .admin-badge {
            background: #ef4444;
            color: white;
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 10px;
        }
        .chat-area { flex: 1; display: flex; flex-direction: column; }
        .rooms {
            display: flex;
            gap: 4px;
            padding: 12px 16px;
            border-bottom: 1px solid #e5e7eb;
        }
        .room-btn {
            padding: 8px 20px;
            border-radius: 20px;
            background: transparent;
            border: none;
            cursor: pointer;
        }
        .room-btn.active {
            background: #4f46e5;
            color: white;
        }
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .message {
            display: flex;
            gap: 12px;
            align-items: flex-start;
        }
        .message-own { justify-content: flex-end; }
        .message-content {
            background: #f3f4f6;
            padding: 10px 14px;
            border-radius: 18px;
            max-width: 65%;
        }
        .message-own .message-content {
            background: #4f46e5;
            color: white;
        }
        .message-name {
            font-weight: 600;
            font-size: 13px;
            cursor: pointer;
        }
        .message-time {
            font-size: 10px;
            opacity: 0.7;
            margin-left: 8px;
        }
        .message-text { margin-top: 4px; word-wrap: break-word; }
        .delete-btn {
            background: none;
            border: none;
            color: #ef4444;
            cursor: pointer;
            margin-left: 8px;
        }
        .system-message {
            text-align: center;
            font-size: 12px;
            color: #6b7280;
            padding: 4px;
        }
        .input-area {
            display: flex;
            gap: 12px;
            padding: 16px;
            border-top: 1px solid #e5e7eb;
        }
        .input-area input {
            flex: 1;
            padding: 12px 18px;
            border: 1px solid #e5e7eb;
            border-radius: 30px;
            outline: none;
        }
        .input-area button {
            background: #4f46e5;
            border: none;
            border-radius: 50%;
            width: 48px;
            height: 48px;
            color: white;
            cursor: pointer;
        }
        @media (max-width: 768px) { .sidebar { display: none; } }
    </style>
</head>
<body>
<div class="chat-container">
    <div class="chat-card">
        <div class="header">
            <h2>💬 Чатик</h2>
            <div>{{ username }} ({{ role }}) <a href="/logout" style="color:white; margin-left:16px;">Выйти</a></div>
        </div>
        <div class="main">
            <div class="sidebar">
                <div class="sidebar-title">👥 Пользователи</div>
                <div id="usersList"></div>
            </div>
            <div class="chat-area">
                <div class="rooms" id="rooms">
                    <button class="room-btn active" data-room="Общая">🏠 Общая</button>
                    <button class="room-btn" data-room="Случайная">🎲 Случайная</button>
                    <button class="room-btn" data-room="Помощь">🆘 Помощь</button>
                </div>
                <div id="messages" class="messages"></div>
                <div class="input-area">
                    <input type="text" id="messageInput" placeholder="Сообщение...">
                    <button id="sendBtn">📤</button>
                </div>
            </div>
        </div>
    </div>
</div>
<script>
    let socket = null;
    let currentRoom = 'Общая';
    let username = '{{ username }}';
    let role = '{{ role }}';
    
    const sendBtn = document.getElementById('sendBtn');
    const messageInput = document.getElementById('messageInput');
    const messagesDiv = document.getElementById('messages');
    
    function addMessage(name, text, time, isOwn, msgRole) {
        const div = document.createElement('div');
        div.className = `message ${isOwn ? 'message-own' : ''}`;
        let badge = msgRole === 'admin' ? ' <span class="admin-badge">ADMIN</span>' : '';
        div.innerHTML = `
            <div class="message-content">
                <div class="message-name">${escapeHtml(name)}${badge}</div>
                <div class="message-text">${escapeHtml(text)}</div>
                <div class="message-time">${time}</div>
            </div>
            ${!isOwn && role === 'admin' ? `<button class="delete-btn" onclick="deleteMsg('${name}', '${text}')">🗑</button>` : ''}
        `;
        messagesDiv.appendChild(div);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    
    window.deleteMsg = function(name, text) {
        if(confirm('Удалить сообщение?')) {
            socket.emit('delete_message', { room: currentRoom, name: name, text: text });
        }
    };
    
    function addSystemMessage(text) {
        const div = document.createElement('div');
        div.className = 'system-message';
        div.textContent = text;
        messagesDiv.appendChild(div);
    }
    
    function escapeHtml(str) {
        return str.replace(/[&<>]/g, function(m) {
            if(m === '&') return '&amp;';
            if(m === '<') return '&lt;';
            if(m === '>') return '&gt;';
            return m;
        });
    }
    
    socket = io();
    socket.emit('join', { name: username, room: currentRoom });
    
    socket.on('history', (history) => {
        messagesDiv.innerHTML = '';
        history.forEach(msg => addMessage(msg.name, msg.text, msg.time, msg.name === username, msg.role));
    });
    
    socket.on('message', (msg) => {
        addMessage(msg.name, msg.text, msg.time, msg.name === username, msg.role);
    });
    
    socket.on('system', addSystemMessage);
    socket.on('users_list', (users) => {
        const container = document.getElementById('usersList');
        container.innerHTML = users.map(u => `<div class="user-item">${escapeHtml(u.name)} ${u.role === 'admin' ? '<span class="admin-badge">ADMIN</span>' : ''}</div>`).join('');
    });
    
    sendBtn.onclick = () => {
        if(messageInput.value.trim()) {
            socket.emit('message', { name: username, text: messageInput.value, room: currentRoom });
            messageInput.value = '';
        }
    };
    
    messageInput.addEventListener('keypress', (e) => {
        if(e.key === 'Enter') sendBtn.click();
    });
    
    document.querySelectorAll('.room-btn').forEach(btn => {
        btn.onclick = () => {
            const newRoom = btn.dataset.room;
            if(newRoom === currentRoom) return;
            socket.emit('switch_room', { name: username, old_room: currentRoom, new_room: newRoom });
            currentRoom = newRoom;
            document.querySelectorAll('.room-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            messagesDiv.innerHTML = '<div class="system-message">⏳ Загрузка...</div>';
        };
    });
    
    socket.emit('get_users');
</script>
</body>
</html>
'''

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template_string(CHAT_PAGE, username=session['username'], role=session.get('role', 'user'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username]['password'] == password:
            session['username'] = username
            session['role'] = users[username]['role']
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
        if len(username) < 3:
            return render_template_string(REGISTER_PAGE, error='Имя слишком короткое (мин. 3 символа)')
        if len(password) < 4:
            return render_template_string(REGISTER_PAGE, error='Пароль слишком короткий (мин. 4 символа)')
        users[username] = {'password': password, 'role': 'user'}
        save_users(users)
        return redirect(url_for('login'))
    return render_template_string(REGISTER_PAGE, error=None)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@socketio.on('join')
def handle_join(data):
    room = data['room']
    join_room(room)
    emit('history', history.get(room, []), to=request.sid)
    emit('system', f'{data["name"]} присоединился', to=room, broadcast=True)

@socketio.on('message')
def handle_message(data):
    room = data['room']
    time_str = datetime.now().strftime('%H:%M:%S')
    message = {'name': data['name'], 'text': data['text'], 'time': time_str, 'role': session.get('role', 'user')}
    history.setdefault(room, []).append(message)
    if len(history[room]) > 50:
        history[room] = history[room][-50:]
    save_messages(history)
    emit('message', message, to=room, broadcast=True)

@socketio.on('delete_message')
def handle_delete(data):
    if session.get('role') != 'admin':
        return
    room = data['room']
    name = data['name']
    text = data['text']
    for msg in history.get(room, []):
        if msg['name'] == name and msg['text'] == text:
            history[room].remove(msg)
            save_messages(history)
            break

@socketio.on('switch_room')
def handle_switch_room(data):
    old_room = data['old_room']
    new_room = data['new_room']
    leave_room(old_room)
    join_room(new_room)
    emit('history', history.get(new_room, []), to=request.sid)
    emit('system', f'{data["name"]} перешёл в {new_room}', to=new_room, broadcast=True)

@socketio.on('get_users')
def handle_get_users():
    emit('users_list', [{'name': u, 'role': users[u]['role']} for u in users])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
