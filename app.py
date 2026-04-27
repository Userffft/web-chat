from flask import Flask, render_template_string, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import os
import json
import hashlib

app = Flask(__name__)
app.secret_key = 'secret-key-2024'
socketio = SocketIO(app, cors_allowed_origins="*")

# Загрузка пользователей
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
            'bio': 'Владелец',
            'friends': [],
            'requests': [],
            'banned': False
        },
        'dimooon': {
            'password': hashlib.sha256('1111'.encode()).hexdigest(),
            'role': 'admin',
            'avatar': '😎',
            'bio': 'Админ',
            'friends': [],
            'requests': [],
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
    return {'Главная': []}

def save_messages(messages):
    with open(MESSAGES_FILE, 'w') as f:
        json.dump(messages, f)

def load_rooms():
    if os.path.exists(ROOMS_FILE):
        with open(ROOMS_FILE, 'r') as f:
            return json.load(f)
    return ['Главная', 'Случайная', 'Помощь']

def save_rooms(rooms):
    with open(ROOMS_FILE, 'w') as f:
        json.dump(rooms, f)

users = load_users()
messages = load_messages()
rooms = load_rooms()

# ШАБЛОНЫ
LOGIN_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Чатик · Вход</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: system-ui;
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
            text-align: center;
        }
        h1 { margin-bottom: 8px; color: #4f46e5; }
        input {
            width: 100%;
            padding: 14px;
            border: 1px solid #ddd;
            border-radius: 24px;
            margin-bottom: 12px;
        }
        button {
            width: 100%;
            padding: 14px;
            background: #4f46e5;
            color: white;
            border: none;
            border-radius: 24px;
            cursor: pointer;
        }
        .error { color: red; margin-bottom: 16px; }
        a { color: #4f46e5; text-decoration: none; }
    </style>
</head>
<body>
    <div class="card">
        <h1>💬 Чатик</h1>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="post">
            <input type="text" name="username" placeholder="Имя" required>
            <input type="password" name="password" placeholder="Пароль" required>
            <button type="submit">Войти</button>
        </form>
        <p style="margin-top: 20px;">Нет аккаунта? <a href="/register">Регистрация</a></p>
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
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: system-ui;
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
            text-align: center;
        }
        h1 { margin-bottom: 24px; color: #4f46e5; }
        input {
            width: 100%;
            padding: 14px;
            border: 1px solid #ddd;
            border-radius: 24px;
            margin-bottom: 12px;
        }
        button {
            width: 100%;
            padding: 14px;
            background: #4f46e5;
            color: white;
            border: none;
            border-radius: 24px;
            cursor: pointer;
        }
        .error { color: red; margin-bottom: 16px; }
        a { color: #4f46e5; text-decoration: none; }
    </style>
</head>
<body>
    <div class="card">
        <h1>📝 Регистрация</h1>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="post">
            <input type="text" name="username" placeholder="Имя (3-20)" required>
            <input type="password" name="password" placeholder="Пароль (мин 4)" required>
            <button type="submit">Создать аккаунт</button>
        </form>
        <p style="margin-top: 20px;">Уже есть аккаунт? <a href="/login">Войти</a></p>
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
    <title>Чатик · {{ username }}</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: system-ui;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
        }
        body.dark {
            background: #1e1b4b;
        }
        .sidebar {
            width: 260px;
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            border-right: 1px solid rgba(0,0,0,0.1);
            display: flex;
            flex-direction: column;
            padding: 16px;
            overflow-y: auto;
        }
        body.dark .sidebar {
            background: #1f2937;
            color: white;
        }
        .user-card {
            text-align: center;
            padding: 16px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            border-radius: 20px;
            color: white;
            margin-bottom: 20px;
            cursor: pointer;
        }
        .avatar {
            font-size: 48px;
            margin-bottom: 8px;
        }
        .section-title {
            font-weight: bold;
            margin: 16px 0 8px 0;
            color: #374151;
        }
        body.dark .section-title {
            color: #9ca3af;
        }
        .room, .user {
            padding: 10px;
            border-radius: 12px;
            cursor: pointer;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .room:hover, .user:hover {
            background: rgba(0,0,0,0.05);
        }
        .room.active {
            background: #4f46e5;
            color: white;
        }
        .add-room {
            display: flex;
            gap: 8px;
            margin-top: 12px;
        }
        .add-room input {
            flex: 1;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 20px;
            outline: none;
        }
        .add-room button {
            background: #4f46e5;
            color: white;
            border: none;
            border-radius: 20px;
            padding: 8px 12px;
            cursor: pointer;
        }
        .chat-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: white;
        }
        body.dark .chat-area {
            background: #111827;
        }
        .chat-header {
            padding: 16px 24px;
            border-bottom: 1px solid #eee;
            background: white;
            display: flex;
            justify-content: space-between;
        }
        body.dark .chat-header {
            background: #1f2937;
            color: white;
            border-color: #374151;
        }
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .message {
            display: flex;
            gap: 10px;
            align-items: flex-start;
        }
        .message.own {
            justify-content: flex-end;
        }
        .message-avatar {
            width: 32px;
            height: 32px;
            background: #4f46e5;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
        }
        .message-content {
            background: #f3f4f6;
            padding: 8px 14px;
            border-radius: 18px;
            max-width: 60%;
        }
        body.dark .message-content {
            background: #374151;
            color: white;
        }
        .message.own .message-content {
            background: #4f46e5;
            color: white;
        }
        .message-name {
            font-size: 12px;
            font-weight: bold;
        }
        .message-time {
            font-size: 10px;
            opacity: 0.6;
        }
        .system {
            text-align: center;
            font-size: 12px;
            color: #6b7280;
            padding: 4px;
        }
        .typing {
            padding: 8px 24px;
            font-size: 12px;
            color: #6b7280;
            font-style: italic;
        }
        .input-area {
            display: flex;
            gap: 12px;
            padding: 16px 24px;
            border-top: 1px solid #eee;
            background: white;
        }
        body.dark .input-area {
            background: #1f2937;
            border-color: #374151;
        }
        .input-area input {
            flex: 1;
            padding: 12px 18px;
            border: 1px solid #ddd;
            border-radius: 30px;
            outline: none;
        }
        body.dark .input-area input {
            background: #374151;
            color: white;
            border-color: #4b5563;
        }
        .input-area button {
            background: #4f46e5;
            border: none;
            border-radius: 50%;
            width: 46px;
            height: 46px;
            color: white;
            cursor: pointer;
        }
        .badge {
            background: #ef4444;
            font-size: 9px;
            padding: 2px 6px;
            border-radius: 12px;
            margin-left: 6px;
        }
        .badge-admin {
            background: #10b981;
        }
        .online-dot {
            width: 8px;
            height: 8px;
            background: #10b981;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
        }
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }
        .modal-content {
            background: white;
            border-radius: 24px;
            padding: 24px;
            max-width: 400px;
            width: 90%;
        }
        body.dark .modal-content {
            background: #1f2937;
            color: white;
        }
        .modal-content input, .modal-content textarea {
            width: 100%;
            padding: 10px;
            margin: 10px 0;
            border-radius: 20px;
            border: 1px solid #ddd;
        }
        .modal-content button {
            background: #4f46e5;
            color: white;
            border: none;
            padding: 12px;
            border-radius: 24px;
            width: 100%;
            cursor: pointer;
        }
        .close {
            float: right;
            font-size: 24px;
            cursor: pointer;
        }
        .btn {
            margin-top: 10px;
            padding: 10px;
            border: none;
            border-radius: 20px;
            cursor: pointer;
            width: 100%;
        }
        .btn-settings {
            background: #e0e7ff;
            color: #4f46e5;
        }
        .btn-logout {
            background: #fee2e2;
            color: #dc2626;
        }
        body.dark .btn-settings {
            background: #374151;
            color: #818cf8;
        }
        body.dark .btn-logout {
            background: #374151;
            color: #f87171;
        }
        @media (max-width: 600px) {
            .sidebar { width: 220px; }
        }
    </style>
</head>
<body>
<div class="sidebar">
    <div class="user-card" id="profileBtn">
        <div class="avatar">{{ avatar }}</div>
        <div><strong>{{ username }}</strong>{% if role == 'owner' %}<span class="badge">ВЛ</span>{% elif role == 'admin' %}<span class="badge badge-admin">АДМ</span>{% endif %}</div>
        <div style="font-size: 11px;">{{ bio[:40] }}</div>
        <div style="font-size: 10px;">{{ role_name }}</div>
    </div>
    <div style="font-weight: bold; margin: 16px 0 8px 0;">📌 Комнаты</div>
    <div id="roomsList"></div>
    {% if role in ['owner', 'admin'] %}
    <div class="add-room">
        <input type="text" id="newRoom" placeholder="Название">
        <button id="createRoom">+</button>
    </div>
    {% endif %}
    <div style="font-weight: bold; margin: 16px 0 8px 0;">👥 Пользователи</div>
    <div id="usersList"></div>
    <div style="font-weight: bold; margin: 16px 0 8px 0;">👫 Друзья</div>
    <div id="friendsList"></div>
    <button class="btn btn-settings" id="settingsBtn">⚙️ Настройки</button>
    <button class="btn btn-logout" id="logoutBtn">🚪 Выйти</button>
</div>
<div class="chat-area">
    <div class="chat-header">
        <span id="roomName">Главная</span>
        <span id="onlineCnt">👥 0</span>
    </div>
    <div id="messages" class="messages"></div>
    <div id="typing" class="typing"></div>
    <div class="input-area">
        <input type="text" id="messageInput" placeholder="Сообщение...">
        <button id="sendBtn">📤</button>
    </div>
</div>

<div id="profileModal" class="modal">
    <div class="modal-content">
        <span class="close" id="closeProfile">&times;</span>
        <h3>👤 Профиль</h3>
        <label>Аватар (эмодзи):</label>
        <input type="text" id="avatarInput" maxlength="2" placeholder="😀">
        <label>О себе:</label>
        <textarea id="bioInput" rows="3" placeholder="О себе...">{{ bio }}</textarea>
        <label>Новое имя:</label>
        <input type="text" id="newName" placeholder="Новое имя">
        <label>Новый пароль:</label>
        <input type="password" id="newPass" placeholder="Новый пароль">
        <button id="saveProfile">💾 Сохранить</button>
    </div>
</div>

<div id="settingsModal" class="modal">
    <div class="modal-content">
        <span class="close" id="closeSettings">&times;</span>
        <h3>⚙️ Настройки</h3>
        <button id="themeBtn" style="background:#e0e7ff;">🌙 Тёмная тема</button>
        <h4 style="margin-top: 20px;">📨 Заявки</h4>
        <div id="requestsList"></div>
        <h4 style="margin-top: 20px;">👑 Команды</h4>
        <p style="font-size: 12px;">• <code>/giveadmin ИМЯ</code></p>
        <p style="font-size: 12px;">• <code>/unadmin ИМЯ</code></p>
        <p style="font-size: 12px;">• <code>/addfriend ИМЯ</code></p>
    </div>
</div>

<script>
    let socket = io();
    let room = 'Главная';
    let username = '{{ username }}';
    let role = '{{ role }}';
    let dark = false;
    let typingUsers = {};
    
    const messagesDiv = document.getElementById('messages');
    const msgInput = document.getElementById('messageInput');
    
    function loadRequests() {
        fetch('/get_requests').then(r => r.json()).then(data => {
            let div = document.getElementById('requestsList');
            if(data.requests && data.requests.length) {
                div.innerHTML = data.requests.map(r => `<div style="display:flex;justify-content:space-between;margin:8px 0;"><span>📨 ${escape(r)}</span><button onclick="acceptReq('${escape(r)}')" style="background:#10b981;border:none;border-radius:16px;padding:4px 12px;color:white;">Принять</button></div>`).join('');
            } else {
                div.innerHTML = '<p>Нет заявок</p>';
            }
        });
    }
    
    window.acceptReq = function(name) {
        fetch('/accept_friend', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({friend: name})
        }).then(r => r.json()).then(data => {
            alert(data.message);
            loadRequests();
        });
    };
    
    function addMsg(id, name, text, time, own, avatar) {
        let div = document.createElement('div');
        div.className = `message ${own ? 'own' : ''}`;
        div.innerHTML = `<div class="message-avatar">${avatar || '👤'}</div>
            <div class="message-content">
                <div class="message-name">${escape(name)}<span class="message-time"> ${time}</span></div>
                <div>${escape(text)}</div>
            </div>`;
        messagesDiv.appendChild(div);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    
    function systemMsg(text) {
        let div = document.createElement('div');
        div.className = 'system';
        div.textContent = text;
        messagesDiv.appendChild(div);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    
    function escape(str) {
        return str.replace(/[&<>]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;'})[m]);
    }
    
    socket.emit('join', { room: room });
    
    socket.on('history', (data) => {
        messagesDiv.innerHTML = '';
        data.forEach(m => addMsg(m.id, m.name, m.text, m.time, m.name === username, m.avatar));
    });
    
    socket.on('message', (m) => {
        addMsg(m.id, m.name, m.text, m.time, m.name === username, m.avatar);
    });
    
    socket.on('system', (data) => systemMsg(data.text));
    
    socket.on('rooms', (list) => {
        let div = document.getElementById('roomsList');
        div.innerHTML = list.map(r => `<div class="room ${r === room ? 'active' : ''}" data-room="${r}">🏠 ${escape(r)}</div>`).join('');
        document.querySelectorAll('.room').forEach(el => {
            el.onclick = () => {
                let r = el.dataset.room;
                if(r === room) return;
                socket.emit('switch', { old: room, new: r });
                room = r;
                document.getElementById('roomName').innerText = room;
                document.querySelectorAll('.room').forEach(i => i.classList.remove('active'));
                el.classList.add('active');
                messagesDiv.innerHTML = '<div class="system">⏳ Загрузка...</div>';
            };
        });
    });
    
    socket.on('users', (list) => {
        let div = document.getElementById('usersList');
        div.innerHTML = list.map(u => `<div class="user" onclick="profile('${escape(u.name)}')"><span class="online-dot"></span> ${u.avatar || '👤'} ${escape(u.name)} ${u.role === 'owner' ? '<span class="badge">ВЛ</span>' : (u.role === 'admin' ? '<span class="badge badge-admin">АДМ</span>' : '')}</div>`).join('');
        document.getElementById('onlineCnt').innerText = `👥 ${list.length}`;
    });
    
    window.profile = function(name) {
        fetch('/user/' + encodeURIComponent(name)).then(r => r.json()).then(data => {
            alert(`${data.username}\n📝 ${data.bio || 'Нет описания'}\n👫 Друзей: ${data.friends || 0}\n⭐ ${data.role}`);
        });
    };
    
    socket.on('friends', (list) => {
        let div = document.getElementById('friendsList');
        if(div) div.innerHTML = list.map(f => `<div class="user" onclick="profile('${escape(f.name)}')">👫 ${escape(f.name)}</div>`).join('');
    });
    
    socket.on('typing', (data) => {
        if(data.typing) typingUsers[data.name] = true;
        else delete typingUsers[data.name];
        let names = Object.keys(typingUsers).filter(n => n !== username);
        document.getElementById('typing').innerText = names.length ? (names.length === 1 ? `${names[0]} печатает...` : `${names.length} человек печатают...`) : '';
    });
    
    document.getElementById('sendBtn').onclick = () => {
        let text = msgInput.value.trim();
        if(!text) return;
        if(text.startsWith('/giveadmin ') && role === 'owner') {
            let target = text.split(' ')[1];
            fetch('/give_admin', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username: target})
            }).then(r => r.json()).then(data => systemMsg(data.message));
            msgInput.value = '';
            return;
        }
        if(text.startsWith('/unadmin ') && role === 'owner') {
            let target = text.split(' ')[1];
            fetch('/remove_admin', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username: target})
            }).then(r => r.json()).then(data => systemMsg(data.message));
            msgInput.value = '';
            return;
        }
        if(text.startsWith('/addfriend ')) {
            let target = text.split(' ')[1];
            fetch('/add_friend', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({friend: target})
            }).then(r => r.json()).then(data => systemMsg(data.message));
            msgInput.value = '';
            return;
        }
        socket.emit('message', { text: text, room: room });
        msgInput.value = '';
    };
    
    msgInput.onkeypress = (e) => {
        if(e.key === 'Enter') document.getElementById('sendBtn').click();
        socket.emit('typing', { room: room, typing: true });
        clearTimeout(window.typingTimeout);
        window.typingTimeout = setTimeout(() => socket.emit('typing', { room: room, typing: false }), 1000);
    };
    
    document.getElementById('createRoom')?.addEventListener('click', () => {
        let name = document.getElementById('newRoom').value.trim();
        if(name) {
            socket.emit('create', { room: name });
            document.getElementById('newRoom').value = '';
        }
    });
    
    // Модалки
    let profileModal = document.getElementById('profileModal');
    let settingsModal = document.getElementById('settingsModal');
    document.getElementById('profileBtn')?.addEventListener('click', () => profileModal.style.display = 'flex');
    document.getElementById('settingsBtn')?.addEventListener('click', () => {
        settingsModal.style.display = 'flex';
        loadRequests();
    });
    document.getElementById('closeProfile')?.addEventListener('click', () => profileModal.style.display = 'none');
    document.getElementById('closeSettings')?.addEventListener('click', () => settingsModal.style.display = 'none');
    window.onclick = (e) => {
        if(e.target === profileModal) profileModal.style.display = 'none';
        if(e.target === settingsModal) settingsModal.style.display = 'none';
    };
    
    document.getElementById('saveProfile')?.addEventListener('click', () => {
        fetch('/update_profile', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                avatar: document.getElementById('avatarInput').value,
                bio: document.getElementById('bioInput').value,
                new_name: document.getElementById('newName').value,
                new_password: document.getElementById('newPass').value
            })
        }).then(r => r.json()).then(data => {
            if(data.success) {
                alert('Сохранено! Страница перезагрузится.');
                location.reload();
            } else alert('Ошибка: ' + data.error);
        });
    });
    
    document.getElementById('themeBtn')?.addEventListener('click', () => {
        dark = !dark;
        if(dark) document.body.classList.add('dark');
        else document.body.classList.remove('dark');
        fetch('/save_theme', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({theme: dark ? 'dark' : 'light'})
        });
    });
    
    document.getElementById('logoutBtn')?.addEventListener('click', () => window.location.href = '/logout');
    
    socket.emit('get_rooms');
    socket.emit('get_users');
</script>
</body>
</html>
'''

# МАРШРУТЫ
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    u = users.get(session['username'])
    if not u or u.get('banned'):
        session.clear()
        return redirect(url_for('login'))
    role_names = {'owner': 'Владелец', 'admin': 'Админ', 'user': 'Пользователь'}
    return render_template_string(CHAT_PAGE, 
        username=session['username'],
        role=u['role'],
        role_name=role_names.get(u['role'], 'Пользователь'),
        avatar=u.get('avatar', '👤'),
        bio=u.get('bio', ''),
        theme=u.get('theme', 'light')
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['username']
        pwd = request.form['password']
        h = hashlib.sha256(pwd.encode()).hexdigest()
        if name in users and users[name]['password'] == h:
            if users[name].get('banned'):
                return render_template_string(LOGIN_PAGE, error='Вы заблокированы')
            session['username'] = name
            return redirect(url_for('index'))
        return render_template_string(LOGIN_PAGE, error='Неверные данные')
    return render_template_string(LOGIN_PAGE)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['username']
        pwd = request.form['password']
        if name in users:
            return render_template_string(REGISTER_PAGE, error='Имя занято')
        if len(name) < 3 or len(name) > 20:
            return render_template_string(REGISTER_PAGE, error='Имя 3-20 символов')
        if len(pwd) < 4:
            return render_template_string(REGISTER_PAGE, error='Пароль минимум 4 символа')
        users[name] = {
            'password': hashlib.sha256(pwd.encode()).hexdigest(),
            'role': 'user',
            'avatar': '👤',
            'bio': '',
            'friends': [],
            'requests': [],
            'banned': False,
            'theme': 'light'
        }
        save_users(users)
        return redirect(url_for('login'))
    return render_template_string(REGISTER_PAGE)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/save_theme', methods=['POST'])
def save_theme():
    if 'username' not in session:
        return jsonify({'error': 'Not logged'}), 401
    data = request.json
    users[session['username']]['theme'] = data.get('theme', 'light')
    save_users(users)
    return jsonify({'success': True})

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'username' not in session:
        return jsonify({'error': 'Not logged'}), 401
    name = session['username']
    data = request.json
    if data.get('avatar'):
        users[name]['avatar'] = data['avatar'][:2]
    if data.get('bio') is not None:
        users[name]['bio'] = data['bio'][:200]
    if data.get('new_name'):
        nn = data['new_name']
        if len(nn) < 3 or len(nn) > 20:
            return jsonify({'error': 'Имя 3-20 символов'}), 400
        if nn in users and nn != name:
            return jsonify({'error': 'Имя занято'}), 400
        users[nn] = users.pop(name)
        session['username'] = nn
    if data.get('new_password') and len(data['new_password']) >= 4:
        users[session['username']]['password'] = hashlib.sha256(data['new_password'].encode()).hexdigest()
    save_users(users)
    return jsonify({'success': True})

@app.route('/give_admin', methods=['POST'])
def give_admin():
    if 'username' not in session or users[session['username']]['role'] != 'owner':
        return jsonify({'message': 'Только владелец'})
    target = request.json.get('username')
    if target in users and users[target]['role'] != 'owner':
        users[target]['role'] = 'admin'
        save_users(users)
        return jsonify({'message': f'{target} теперь админ'})
    return jsonify({'message': 'Не найден'})

@app.route('/remove_admin', methods=['POST'])
def remove_admin():
    if 'username' not in session or users[session['username']]['role'] != 'owner':
        return jsonify({'message': 'Только владелец'})
    target = request.json.get('username')
    if target in users and users[target]['role'] == 'admin':
        users[target]['role'] = 'user'
        save_users(users)
        return jsonify({'message': f'У {target} снята админка'})
    return jsonify({'message': 'Не найден'})

@app.route('/add_friend', methods=['POST'])
def add_friend():
    if 'username' not in session:
        return jsonify({'message': 'Войдите'})
    name = session['username']
    target = request.json.get('friend')
    if target not in users:
        return jsonify({'message': 'Не найден'})
    if target == name:
        return jsonify({'message': 'Себя нельзя'})
    if target in users[name]['friends']:
        return jsonify({'message': 'Уже друг'})
    if target in users[name]['requests']:
        return jsonify({'message': 'Заявка уже отправлена'})
    users[target]['requests'].append(name)
    save_users(users)
    return jsonify({'message': f'Заявка отправлена {target}'})

@app.route('/accept_friend', methods=['POST'])
def accept_friend():
    if 'username' not in session:
        return jsonify({'message': 'Войдите'})
    name = session['username']
    target = request.json.get('friend')
    if target not in users[name]['requests']:
        return jsonify({'message': 'Нет заявки'})
    users[name]['requests'].remove(target)
    users[name]['friends'].append(target)
    users[target]['friends'].append(name)
    save_users(users)
    return jsonify({'message': f'Вы приняли заявку от {target}'})

@app.route('/get_requests')
def get_requests():
    if 'username' not in session:
        return jsonify({'requests': []})
    return jsonify({'requests': users[session['username']].get('requests', [])})

@app.route('/user/<name>')
def user_info(name):
    if name not in users:
        return jsonify({'error': 'Not found'}), 404
    u = users[name]
    return jsonify({
        'username': name,
        'bio': u.get('bio', ''),
        'role': {'owner': 'Владелец', 'admin': 'Админ', 'user': 'Пользователь'}.get(u.get('role'), 'Пользователь'),
        'friends': len(u.get('friends', []))
    })

# SOCKET.IO
@socketio.on('join')
def on_join(data):
    if '
