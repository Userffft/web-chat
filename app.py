from flask import Flask, render_template_string, request, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import os
import json
import hashlib

app = Flask(__name__)
app.secret_key = 'chatic-super-secret-key-2024'
socketio = SocketIO(app, cors_allowed_origins="*")

# Файлы для хранения данных
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
            'banned': False,
            'created_at': datetime.now().isoformat()
        }
    }

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

def load_messages():
    if os.path.exists(MESSAGES_FILE):
        with open(MESSAGES_FILE, 'r') as f:
            return json.load(f)
    return {'Общая': []}

def save_messages(messages):
    with open(MESSAGES_FILE, 'w') as f:
        json.dump(messages, f)

def load_rooms():
    if os.path.exists(ROOMS_FILE):
        with open(ROOMS_FILE, 'r') as f:
            return json.load(f)
    return ['Общая', 'Случайная', 'Помощь']

def save_rooms(rooms):
    with open(ROOMS_FILE, 'w') as f:
        json.dump(rooms, f)

users = load_users()
messages = load_messages()
rooms = load_rooms()

# HTML шаблоны
LOGIN_TEMPLATE = '''
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
            background: linear-gradient(135deg, #1e1b4b 0%, #4c1d95 50%, #7e22ce 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .card {
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            border-radius: 48px;
            padding: 48px;
            max-width: 440px;
            width: 100%;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5);
            border: 1px solid rgba(255,255,255,0.2);
        }
        h1 {
            text-align: center;
            margin-bottom: 8px;
            font-size: 2.5rem;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle {
            text-align: center;
            color: #6b7280;
            margin-bottom: 32px;
        }
        input {
            width: 100%;
            padding: 16px 20px;
            border: 2px solid #e5e7eb;
            border-radius: 32px;
            margin-bottom: 16px;
            font-size: 16px;
            outline: none;
            transition: all 0.2s;
        }
        input:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102,126,234,0.1);
        }
        button {
            width: 100%;
            padding: 16px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 32px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover { transform: translateY(-2px); }
        .error {
            background: #fee2e2;
            color: #dc2626;
            padding: 12px;
            border-radius: 24px;
            margin-bottom: 20px;
            text-align: center;
        }
        .footer {
            text-align: center;
            margin-top: 24px;
            color: #6b7280;
        }
        a { color: #667eea; text-decoration: none; font-weight: 500; }
    </style>
</head>
<body>
    <div class="card">
        <h1>💬 Чатик</h1>
        <div class="subtitle">Общайся с друзьями</div>
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

REGISTER_TEMPLATE = '''
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
            background: linear-gradient(135deg, #1e1b4b 0%, #4c1d95 50%, #7e22ce 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .card {
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            border-radius: 48px;
            padding: 48px;
            max-width: 440px;
            width: 100%;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5);
        }
        h1 {
            text-align: center;
            margin-bottom: 32px;
            font-size: 2rem;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        input {
            width: 100%;
            padding: 16px 20px;
            border: 2px solid #e5e7eb;
            border-radius: 32px;
            margin-bottom: 16px;
            font-size: 16px;
            outline: none;
        }
        input:focus { border-color: #667eea; box-shadow: 0 0 0 3px rgba(102,126,234,0.1); }
        button {
            width: 100%;
            padding: 16px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 32px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
        }
        button:hover { transform: translateY(-2px); }
        .error {
            background: #fee2e2;
            color: #dc2626;
            padding: 12px;
            border-radius: 24px;
            margin-bottom: 20px;
            text-align: center;
        }
        .footer {
            text-align: center;
            margin-top: 24px;
            color: #6b7280;
        }
        a { color: #667eea; text-decoration: none; font-weight: 500; }
    </style>
</head>
<body>
    <div class="card">
        <h1>📝 Создать аккаунт</h1>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="post">
            <input type="text" name="username" placeholder="Имя (от 3 до 20 символов)" required autofocus>
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

CHAT_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Чатик · {{ username }}</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #1e1b4b 0%, #4c1d95 50%, #7e22ce 100%);
            height: 100vh;
            overflow: hidden;
        }
        .app { display: flex; height: 100vh; }
        .sidebar {
            width: 300px;
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            border-right: 1px solid rgba(0,0,0,0.1);
            display: flex;
            flex-direction: column;
            overflow-y: auto;
        }
        .user-info {
            padding: 24px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            text-align: center;
        }
        .user-avatar { font-size: 64px; margin-bottom: 12px; }
        .user-name { font-size: 1.3rem; font-weight: 700; }
        .user-role { font-size: 0.8rem; opacity: 0.9; margin-top: 4px; }
        .sidebar-section { padding: 16px 20px; border-bottom: 1px solid #e5e7eb; }
        .sidebar-title { font-weight: 600; margin-bottom: 12px; color: #374151; display: flex; justify-content: space-between; }
        .room-item, .user-item {
            padding: 10px 12px;
            border-radius: 12px;
            cursor: pointer;
            transition: background 0.2s;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .room-item:hover, .user-item:hover { background: #f3f4f6; }
        .room-item.active { background: #e0e7ff; color: #4f46e5; font-weight: 500; }
        .create-room {
            margin-top: 12px;
            padding: 8px;
            background: #f3f4f6;
            border-radius: 24px;
            display: flex;
            gap: 8px;
        }
        .create-room input { flex: 1; padding: 8px 12px; border: none; border-radius: 20px; outline: none; }
        .create-room button { background: #4f46e5; color: white; border: none; border-radius: 20px; padding: 8px 16px; cursor: pointer; }
        .chat-main { flex: 1; display: flex; flex-direction: column; background: rgba(255,255,255,0.95); }
        .chat-header {
            padding: 16px 24px;
            border-bottom: 1px solid #e5e7eb;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: white;
        }
        .chat-room-name { font-size: 1.3rem; font-weight: 700; display: flex; align-items: center; gap: 12px; }
        .messages-area {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .message {
            display: flex;
            gap: 12px;
            align-items: flex-start;
            animation: fadeIn 0.2s ease;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .message-own { justify-content: flex-end; }
        .message-avatar {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }
        .message-content {
            background: #f3f4f6;
            padding: 10px 16px;
            border-radius: 20px;
            max-width: 60%;
            border-bottom-left-radius: 4px;
        }
        .message-own .message-content {
            background: #4f46e5;
            color: white;
            border-bottom-right-radius: 4px;
            border-bottom-left-radius: 20px;
        }
        .message-header {
            display: flex;
            align-items: baseline;
            gap: 8px;
            margin-bottom: 4px;
            flex-wrap: wrap;
        }
        .message-name { font-weight: 700; font-size: 0.85rem; cursor: pointer; }
        .message-time { font-size: 0.65rem; opacity: 0.7; }
        .message-text { word-wrap: break-word; line-height: 1.4; }
        .message-actions { display: flex; gap: 8px; margin-top: 6px; }
        .msg-action { background: none; border: none; font-size: 0.7rem; cursor: pointer; opacity: 0.6; padding: 2px 6px; border-radius: 12px; }
        .msg-action:hover { opacity: 1; background: rgba(0,0,0,0.1); }
        .system-message {
            text-align: center;
            font-size: 0.75rem;
            color: #6b7280;
            padding: 8px;
            background: #f9fafb;
            border-radius: 20px;
            margin: 4px 0;
        }
        .input-area {
            padding: 16px 24px;
            border-top: 1px solid #e5e7eb;
            display: flex;
            gap: 12px;
            background: white;
        }
        .input-area input {
            flex: 1;
            padding: 14px 20px;
            border: 1px solid #e5e7eb;
            border-radius: 40px;
            outline: none;
            font-size: 14px;
        }
        .input-area input:focus { border-color: #4f46e5; }
        .input-area button {
            width: 48px;
            height: 48px;
            background: #4f46e5;
            border: none;
            border-radius: 50%;
            color: white;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .input-area button:hover { transform: scale(1.05); }
        .typing-indicator {
            padding: 8px 24px;
            font-size: 0.75rem;
            color: #6b7280;
            font-style: italic;
        }
        .badge-owner { background: #ef4444; color: white; font-size: 10px; padding: 2px 8px; border-radius: 20px; margin-left: 6px; }
        .badge-admin { background: #10b981; color: white; font-size: 10px; padding: 2px 8px; border-radius: 20px; margin-left: 6px; }
        .badge-moder { background: #f59e0b; color: white; font-size: 10px; padding: 2px 8px; border-radius: 20px; margin-left: 6px; }
        @media (max-width: 768px) { .sidebar { display: none; } .message-content { max-width: 85%; } }
    </style>
</head>
<body>
<div class="app">
    <div class="sidebar">
        <div class="user-info">
            <div class="user-avatar">{{ avatar }}</div>
            <div class="user-name">{{ username }}{% if role == 'owner' %}<span class="badge-owner">ВЛАДЕЛЕЦ</span>{% elif role == 'admin' %}<span class="badge-admin">ADMIN</span>{% elif role == 'moderator' %}<span class="badge-moder">MODER</span>{% endif %}</div>
            <div class="user-role">{{ role_display }}</div>
        </div>
        <div class="sidebar-section">
            <div class="sidebar-title"><i class="fas fa-door-open"></i> Комнаты</div>
            <div id="roomsList"></div>
            {% if role in ['owner', 'admin'] %}
            <div class="create-room">
                <input type="text" id="newRoomName" placeholder="Название комнаты">
                <button id="createRoomBtn">+</button>
            </div>
            {% endif %}
        </div>
        <div class="sidebar-section">
            <div class="sidebar-title"><i class="fas fa-users"></i> Пользователи</div>
            <div id="usersList"></div>
        </div>
    </div>
    <div class="chat-main">
        <div class="chat-header">
            <div class="chat-room-name"><i class="fas fa-hashtag"></i> <span id="currentRoomSpan">Общая</span></div>
            <div><i class="fas fa-search" id="searchBtn" style="cursor: pointer;"></i></div>
        </div>
        <div id="messages" class="messages-area"></div>
        <div id="typingIndicator" class="typing-indicator"></div>
        <div class="input-area">
            <button id="emojiBtn"><i class="far fa-smile"></i></button>
            <input type="text" id="messageInput" placeholder="Сообщение...">
            <button id="sendBtn"><i class="fas fa-paper-plane"></i></button>
        </div>
    </div>
</div>
<script>
    let socket = null;
    let currentRoom = 'Общая';
    let username = '{{ username }}';
    let role = '{{ role }}';
    let typingTimeout = null;
    let typingUsers = {};
    
    const messagesDiv = document.getElementById('messages');
    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    const typingIndicator = document.getElementById('typingIndicator');
    
    function addMessage(id, name, text, time, isOwn, msgRole, avatar) {
        const div = document.createElement('div');
        div.className = `message ${isOwn ? 'message-own' : ''}`;
        div.dataset.id = id;
        let roleBadge = '';
        if(msgRole === 'owner') roleBadge = '<span class="badge-owner">ВЛ</span>';
        else if(msgRole === 'admin') roleBadge = '<span class="badge-admin">ADM</span>';
        else if(msgRole === 'moderator') roleBadge = '<span class="badge-moder">MOD</span>';
        div.innerHTML = `
            <div class="message-avatar">${avatar || '💬'}</div>
            <div class="message-content">
                <div class="message-header">
                    <span class="message-name">${escapeHtml(name)}${roleBadge}</span>
                    <span class="message-time">${time}</span>
                </div>
                <div class="message-text">${escapeHtml(text)}</div>
                ${(role === 'owner' || role === 'admin' || (role === 'moderator' && !isOwn) || isOwn) ? 
                    `<div class="message-actions">
                        <button class="msg-action" onclick="deleteMessage('${id}')"><i class="fas fa-trash"></i></button>
                        ${(!isOwn && role === 'owner') ? `<button class="msg-action" onclick="banUser('${name}')"><i class="fas fa-ban"></i></button>` : ''}
                    </div>` : ''}
            </div>
        `;
        messagesDiv.appendChild(div);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    
    function addSystemMessage(text) {
        const div = document.createElement('div');
        div.className = 'system-message';
        div.textContent = text;
        messagesDiv.appendChild(div);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    
    function escapeHtml(str) {
        return str.replace(/[&<>]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;'})[m]);
    }
    
    window.deleteMessage = function(msgId) {
        if(confirm('Удалить сообщение?')) {
            socket.emit('delete_message', { messageId: msgId, room: currentRoom });
        }
    };
    
    window.banUser = function(user) {
        if(confirm(`Заблокировать пользователя ${user}?`)) {
            socket.emit('ban_user', { username: user, room: currentRoom });
        }
    };
    
    function updateTypingIndicator() {
        const names = Object.keys(typingUsers).filter(n => n !== username);
        typingIndicator.textContent = names.length ? (names.length === 1 ? `${names[0]} печатает...` : `${names.length} человек печатают...`) : '';
    }
    
    socket = io();
    socket.emit('join', { room: currentRoom });
    
    socket.on('history', (history) => {
        messagesDiv.innerHTML = '';
        history.forEach(msg => addMessage(msg.id, msg.name, msg.text, msg.time, msg.name === username, msg.role, msg.avatar));
    });
    
    socket.on('message', (msg) => {
        addMessage(msg.id, msg.name, msg.text, msg.time, msg.name === username, msg.role, msg.avatar);
    });
    
    socket.on('system', addSystemMessage);
    socket.on('typing', (data) => {
        if(data.typing) typingUsers[data.name] = true;
        else delete typingUsers[data.name];
        updateTypingIndicator();
    });
    
    socket.on('rooms_list', (roomsData) => {
        const container = document.getElementById('roomsList');
        container.innerHTML = roomsData.map(r => `<div class="room-item ${r === currentRoom ? 'active' : ''}" data-room="${r}">🏠 ${escapeHtml(r)}</div>`).join('');
        document.querySelectorAll('.room-item').forEach(el => {
            el.onclick = () => {
                const newRoom = el.dataset.room;
                if(newRoom === currentRoom) return;
                socket.emit('switch_room', { old_room: currentRoom, new_room: newRoom });
                currentRoom = newRoom;
                document.getElementById('currentRoomSpan').textContent = currentRoom;
                document.querySelectorAll('.room-item').forEach(i => i.classList.remove('active'));
                el.classList.add('active');
                messagesDiv.innerHTML = '<div class="system-message">⏳ Загрузка...</div>';
            };
        });
    });
    
    socket.on('users_list', (usersData) => {
        const container = document.getElementById('usersList');
        container.innerHTML = usersData.map(u => `<div class="user-item"><span>${u.avatar || '👤'} ${escapeHtml(u.name)}</span> ${u.role === 'owner' ? '<span class="badge-owner">ВЛ</span>' : (u.role === 'admin' ? '<span class="badge-admin">ADM</span>' : (u.role === 'moderator' ? '<span class="badge-moder">MOD</span>' : ''))}</div>`).join('');
    });
    
    socket.on('banned', () => {
        alert('Вы были заблокированы!');
        window.location.href = '/logout';
    });
    
    sendBtn.onclick = () => {
        if(messageInput.value.trim()) {
            socket.emit('message', { text: messageInput.value, room: currentRoom });
            messageInput.value = '';
        }
    };
    
    messageInput.onkeypress = (e) => {
        if(e.key === 'Enter') sendBtn.click();
        socket.emit('typing', { room: currentRoom, typing: true });
        clearTimeout(typingTimeout);
        typingTimeout = setTimeout(() => socket.emit('typing', { room: currentRoom, typing: false }), 1000);
    };
    
    document.getElementById('createRoomBtn')?.addEventListener('click', () => {
        const newRoom = document.getElementById('newRoomName').value.trim();
        if(newRoom) {
            socket.emit('create_room', { room: newRoom });
            document.getElementById('newRoomName').value = '';
        }
    });
    
    document.getElementById('searchBtn')?.addEventListener('click', () => {
        const query = prompt('Поиск сообщений:');
        if(query) {
            const messages = document.querySelectorAll('.message-text');
            let found = false;
            messages.forEach(msg => {
                if(msg.textContent.toLowerCase().includes(query.toLowerCase())) {
                    msg.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    msg.style.background = '#fef3c7';
                    setTimeout(() => msg.style.background = '', 2000);
                    found = true;
                }
            });
            if(!found) alert('Ничего не найдено');
        }
    });
    
    document.getElementById('emojiBtn')?.addEventListener('click', () => {
        const emojis = ['😀','😂','❤️','👍','🎉','🔥','😍','🥹','😭','🤔','👋','🙏','✨','💯','😎','🥳'];
        const picker = document.createElement('div');
        picker.style.position = 'fixed';
        picker.style.bottom = '80px';
        picker.style.left = '20px';
        picker.style.background = 'white';
        picker.style.borderRadius = '16px';
        picker.style.padding = '12px';
        picker.style.display = 'grid';
        picker.style.gridTemplateColumns = 'repeat(6, 1fr)';
        picker.style.gap = '8px';
        picker.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
        picker.style.zIndex = '1000';
        emojis.forEach(emoji => {
            const span = document.createElement('span');
            span.textContent = emoji;
            span.style.fontSize = '24px';
            span.style.cursor = 'pointer';
            span.onclick = () => {
                messageInput.value += emoji;
                messageInput.focus();
                picker.remove();
            };
            picker.appendChild(span);
        });
        document.body.appendChild(picker);
        setTimeout(() => picker.remove(), 5000);
    });
    
    socket.emit('get_rooms');
    socket.emit('get_users');
</script>
</body>
</html>
'''

# Маршруты Flask
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    user = users.get(session['username'])
    if not user or user.get('banned'):
        session.clear()
        return redirect(url_for('login'))
    role_display = {'owner': 'Владелец', 'admin': 'Администратор', 'moderator': 'Модератор', 'user': 'Пользователь'}.get(user['role'], 'Пользователь')
    return render_template_string(CHAT_TEMPLATE, 
                                 username=session['username'],
                                 role=user['role'],
                                 role_display=role_display,
                                 avatar=user.get('avatar', '💬'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed = hashlib.sha256(password.encode()).hexdigest()
        if username in users and users[username]['password'] == hashed:
            if users[username].get('banned'):
                return render_template_string(LOGIN_TEMPLATE, error='Вы заблокированы')
            session['username'] = username
            return redirect(url_for('index'))
        return render_template_string(LOGIN_TEMPLATE, error='Неверное имя или пароль')
    return render_template_string(LOGIN_TEMPLATE, error=None)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users:
            return render_template_string(REGISTER_TEMPLATE, error='Пользователь уже существует')
        if len(username) < 3 or len(username) > 20:
            return render_template_string(REGISTER_TEMPLATE, error='Имя должно быть от 3 до 20 символов')
        if len(password) < 4:
            return render_template_string(REGISTER_TEMPLATE, error='Пароль должен быть минимум 4 символа')
        users[username] = {
            'password': hashlib.sha256(password.encode()).hexdigest(),
            'role': 'user',
            'avatar': '👤',
            'banned': False,
            'created_at': datetime.now().isoformat()
        }
        save_users(users)
        return redirect(url_for('login'))
    return render_template_string(REGISTER_TEMPLATE, error=None)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# SocketIO события
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
    if len(text) > 500:
        emit('system', 'Сообщение слишком длинное', to=request.sid)
        return
    msg_id = str(int(datetime.now().timestamp() * 1000))
    message = {
        'id': msg_id,
        'name': username,
        'text': text,
        'time': datetime.now().strftime('%H:%M:%S'),
        'role': users[username]['role'],
        'avatar': users[username].get('avatar', '👤')
    }
    messages.setdefault(room, []).append(message)
    if len(messages[room]) > 200:
        messages[room] = messages[room][-200:]
    save_messages(messages)
    emit('message', message, to=room, broadcast=True)

@socketio.on('delete_message')
def handle_delete(data):
    username = session.get('username')
    if not username:
        return
    role = users[username]['role']
    msg_id = data['messageId']
    room = data['room']
    for i, msg in enumerate(messages.get(room, [])):
        if msg.get('id') == msg_id:
            if role == 'owner' or (role == 'admin' and msg['name'] != username) or msg['name'] == username:
                messages[room].pop(i)
                save_messages(messages)
                emit('system', f'Сообщение от {msg["name"]} удалено', to=room, broadcast=True)
            break

@socketio.on('ban_user')
def handle_ban(data):
    username = session.get('username')
    if not username or users[username]['role'] not in ['owner', 'admin']:
        return
    target = data['username']
    room = data.get('room', 'Общая')
    if target in users and users[target]['role'] != 'owner':
        users[target]['banned'] = True
        save_users(users)
        emit('system', f'{target} заблокирован', to=room, broadcast=True)

@socketio.on('typing')
def handle_typing(data):
    username = session.get('username')
    if not username:
        return
    emit('typing', {'name': username, 'typing': data['typing']}, to=data['room'], broadcast=True, include_self=False)

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

@socketio.on('create_room')
def handle_create_room(data):
    username = session.get('username')
    if not username or users[username]['role'] not in ['owner', 'admin']:
        return
    new_room = data['room'].strip()
    if new_room and new_room not in rooms:
        rooms.append(new_room)
        messages[new_room] = []
        save_rooms(rooms)
        save_messages(messages)
        emit('rooms_list', rooms, broadcast=True)

@socketio.on('get_rooms')
def handle_get_rooms():
    emit('rooms_list', rooms)

@socketio.on('get_users')
def handle_get_users():
    users_list = [{'name': name, 'role': data['role'], 'avatar': data.get('avatar', '👤')} 
                  for name, data in users.items() if not data.get('banned')]
    emit('users_list', users_list, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe
