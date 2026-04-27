from flask import Flask, render_template_string, request, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import os
import json
import hashlib

app = Flask(__name__)
app.secret_key = 'chatic-super-secret-key-2024'
socketio = SocketIO(app, cors_allowed_origins="*")

# ==================== ФАЙЛЫ ДАННЫХ ====================
USERS_FILE = 'users.json'
MESSAGES_FILE = 'messages.json'
ROOMS_FILE = 'rooms.json'
SETTINGS_FILE = 'settings.json'

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
            'theme': 'light'
        },
        'dimooon': {
            'password': hashlib.sha256('1111'.encode()).hexdigest(),
            'role': 'admin',
            'avatar': '😎',
            'banned': False,
            'theme': 'light'
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

def save_rooms(rooms):
    with open(ROOMS_FILE, 'w') as f:
        json.dump(rooms, f)

users = load_users()
messages = load_messages()
rooms = load_rooms()

# ==================== HTML ШАБЛОНЫ ====================
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
            background: linear-gradient(135deg, #1e1b4b 0%, #4c1d95 50%, #7e22ce 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .card {
            background: rgba(255,255,255,0.98);
            border-radius: 48px;
            padding: 48px;
            max-width: 440px;
            width: 100%;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
            text-align: center;
        }
        h1 {
            font-size: 2.5rem;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }
        .subtitle { color: #6b7280; margin-bottom: 32px; }
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
            transition: transform 0.2s;
        }
        button:hover { transform: translateY(-2px); }
        .error {
            background: #fee2e2;
            color: #dc2626;
            padding: 12px;
            border-radius: 24px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        .footer {
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
        <div class="footer">Нет аккаунта? <a href="/register">Зарегистрироваться</a></div>
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
            background: linear-gradient(135deg, #1e1b4b 0%, #4c1d95 50%, #7e22ce 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .card {
            background: rgba(255,255,255,0.98);
            border-radius: 48px;
            padding: 48px;
            max-width: 440px;
            width: 100%;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
        }
        h1 {
            text-align: center;
            font-size: 2rem;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
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
            <input type="text" name="username" placeholder="Имя (3-20 символов)" required autofocus>
            <input type="password" name="password" placeholder="Пароль (мин. 4)" required>
            <button type="submit">Зарегистрироваться</button>
        </form>
        <div class="footer">Уже есть аккаунт? <a href="/login">Войти</a></div>
    </div>
</body>
</html>
'''

CHAT_PAGE = '''
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
            width: 280px;
            background: rgba(255,255,255,0.98);
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
        .user-avatar { font-size: 56px; margin-bottom: 12px; cursor: pointer; }
        .user-name { font-size: 1.2rem; font-weight: 700; }
        .user-role { font-size: 0.75rem; opacity: 0.9; margin-top: 4px; }
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
        .chat-main { flex: 1; display: flex; flex-direction: column; background: white; }
        .chat-header {
            padding: 16px 24px;
            border-bottom: 1px solid #e5e7eb;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: white;
        }
        .chat-room-name { font-size: 1.2rem; font-weight: 700; display: flex; align-items: center; gap: 12px; }
        .messages-area {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            background: #f9fafb;
        }
        .message {
            display: flex;
            gap: 12px;
            align-items: flex-start;
            animation: fadeIn 0.2s ease;
            position: relative;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .message-own { justify-content: flex-end; }
        .message-avatar {
            width: 36px;
            height: 36px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            cursor: pointer;
        }
        .message-content {
            background: white;
            padding: 8px 14px;
            border-radius: 18px;
            max-width: 60%;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        .message-own .message-content {
            background: #4f46e5;
            color: white;
        }
        .message-header {
            display: flex;
            align-items: baseline;
            gap: 8px;
            margin-bottom: 4px;
            flex-wrap: wrap;
        }
        .message-name { font-weight: 700; font-size: 0.8rem; cursor: pointer; }
        .message-time { font-size: 0.65rem; opacity: 0.6; }
        .message-text { word-wrap: break-word; line-height: 1.4; font-size: 0.9rem; }
        .message-actions {
            position: absolute;
            right: 5px;
            top: 5px;
            display: flex;
            gap: 4px;
            opacity: 0;
            transition: opacity 0.2s;
        }
        .message:hover .message-actions { opacity: 1; }
        .msg-action {
            background: #374151;
            border: none;
            border-radius: 50%;
            width: 24px;
            height: 24px;
            color: white;
            cursor: pointer;
            font-size: 0.65rem;
        }
        .system-message {
            text-align: center;
            font-size: 0.7rem;
            color: #6b7280;
            padding: 6px;
            background: #f3f4f6;
            border-radius: 16px;
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
            padding: 12px 20px;
            border: 1px solid #e5e7eb;
            border-radius: 30px;
            outline: none;
            font-size: 14px;
        }
        .input-area input:focus { border-color: #4f46e5; }
        .input-area button {
            width: 44px;
            height: 44px;
            background: #4f46e5;
            border: none;
            border-radius: 50%;
            color: white;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .input-area button:hover { transform: scale(1.05); }
        .typing-indicator {
            padding: 6px 24px;
            font-size: 0.7rem;
            color: #6b7280;
            font-style: italic;
            background: #f9fafb;
        }
        .badge-owner { background: #ef4444; color: white; font-size: 9px; padding: 2px 6px; border-radius: 12px; margin-left: 6px; }
        .badge-admin { background: #10b981; color: white; font-size: 9px; padding: 2px 6px; border-radius: 12px; margin-left: 6px; }
        .badge-moder { background: #f59e0b; color: white; font-size: 9px; padding: 2px 6px; border-radius: 12px; margin-left: 6px; }
        @media (max-width: 680px) { .sidebar { display: none; } .message-content { max-width: 85%; } }
    </style>
</head>
<body>
<div class="app">
    <div class="sidebar">
        <div class="user-info">
            <div class="user-avatar">{{ avatar }}</div>
            <div class="user-name">{{ username }}{% if role == 'owner' %}<span class="badge-owner">ВЛАДЕЛЕЦ</span>{% elif role == 'admin' %}<span class="badge-admin">ADMIN</span>{% elif role == 'moderator' %}<span class="badge-moder">МОДЕР</span>{% endif %}</div>
            <div class="user-role">{{ role_display }}</div>
        </div>
        <div class="sidebar-section">
            <div class="sidebar-title"><i class="fas fa-door-open"></i> Комнаты</div>
            <div id="roomsList"></div>
            {% if role in ['owner', 'admin'] %}
            <div class="create-room">
                <input type="text" id="newRoomName" placeholder="Название">
                <button id="createRoomBtn">+</button>
            </div>
            {% endif %}
        </div>
        <div class="sidebar-section">
            <div class="sidebar-title"><i class="fas fa-users"></i> Пользователи</div>
            <div id="usersList"></div>
        </div>
        <div class="sidebar-section">
            <div class="sidebar-title"><i class="fas fa-palette"></i> Настройки</div>
            <button id="themeBtn" style="width:100%; padding:10px; background:#e0e7ff; border:none; border-radius:20px; cursor:pointer; margin-bottom:8px;">🌙 Тёмная тема</button>
            <button id="logoutBtn" style="width:100%; padding:10px; background:#fee2e2; border:none; border-radius:20px; cursor:pointer; color:#dc2626;">🚪 Выйти</button>
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
            <input type="text" id="messageInput" placeholder="Напишите сообщение...">
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
    
    function addMessage(id, name, text, time, isOwn, msgRole, avatar, isEdited) {
        const div = document.createElement('div');
        div.className = `message ${isOwn ? 'message-own' : ''}`;
        div.dataset.id = id;
        let roleBadge = '';
        if(msgRole === 'owner') roleBadge = '<span class="badge-owner">ВЛ</span>';
        else if(msgRole === 'admin') roleBadge = '<span class="badge-admin">ADM</span>';
        else if(msgRole === 'moderator') roleBadge = '<span class="badge-moder">МОД</span>';
        let editMark = isEdited ? ' <i class="fas fa-pencil-alt" style="font-size:9px;"></i>' : '';
        div.innerHTML = `
            <div class="message-avatar" onclick="startPrivateChat('${name}')">${avatar || '💬'}</div>
            <div class="message-content">
                <div class="message-header">
                    <span class="message-name" onclick="startPrivateChat('${name}')">${escapeHtml(name)}${roleBadge}</span>
                    <span class="message-time">${time}${editMark}</span>
                </div>
                <div class="message-text">${escapeHtml(text)}</div>
            </div>
            <div class="message-actions">
                ${!isOwn && (role === 'owner' || role === 'admin') ? `<button class="msg-action" onclick="deleteMessage('${id}')"><i class="fas fa-trash"></i></button>` : ''}
                ${isOwn ? `<button class="msg-action" onclick="editMessage('${id}')"><i class="fas fa-edit"></i></button>` : ''}
                ${(!isOwn && role === 'owner') ? `<button class="msg-action" onclick="banUser('${name}')"><i class="fas fa-ban"></i></button>` : ''}
                <button class="msg-action" onclick="replyTo('${escapeHtml(name)}', '${escapeHtml(text.substring(0, 40))}')"><i class="fas fa-reply"></i></button>
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
    
    window.deleteMessage = function(id) {
        if(confirm('Удалить сообщение?')) socket.emit('delete_message', { messageId: id, room: currentRoom });
    };
    
    window.editMessage = function(id) {
        const newText = prompt('Новый текст:');
        if(newText) socket.emit('edit_message', { messageId: id, room: currentRoom, new_text: newText });
    };
    
    window.banUser = function(user) {
        if(confirm(`Заблокировать ${user}?`)) socket.emit('ban_user', { username: user, room: currentRoom });
    };
    
    window.startPrivateChat = function(user) {
        const msg = prompt(`Личное сообщение для ${user}:`);
        if(msg) {
            socket.emit('private_message', { target: user, text: msg });
            addSystemMessage(`✉️ Личное сообщение для ${user}: ${msg}`);
        }
    };
    
    window.replyTo = function(name, text) {
        messageInput.value = `@${name}: `;
        messageInput.focus();
    };
    
    function updateTypingIndicator() {
        const names = Object.keys(typingUsers).filter(n => n !== username);
        typingIndicator.textContent = names.length ? (names.length === 1 ? `${names[0]} печатает...` : `${names.length} человек печатают...`) : '';
    }
    
    socket = io();
    socket.emit('join', { room: currentRoom });
    
    socket.on('history', (history) => {
        messagesDiv.innerHTML = '';
        history.forEach(msg => addMessage(msg.id, msg.name, msg.text, msg.time, msg.name === username, msg.role, msg.avatar, msg.edited));
    });
    
    socket.on('message', (msg) => {
        addMessage(msg.id, msg.name, msg.text, msg.time, msg.name === username, msg.role, msg.avatar, msg.edited);
        if(msg.name !== username && role === 'user' && !document.hasFocus()) {
            document.title = '🔔 Новое сообщение!';
            setTimeout(() => { if(document.title === '🔔 Новое сообщение!') document.title = 'Чатик'; }, 3000);
        }
    });
    
    socket.on('message_update', (data) => {
        const el = document.querySelector(`.message[data-id="${data.id}"] .message-text`);
        if(el) el.innerHTML = escapeHtml(data.new_text) + ' <i class="fas fa-pencil-alt" style="font-size:9px;"></i>';
    });
    
    socket.on('system', addSystemMessage);
    
    socket.on('typing', (data) => {
        if(data.typing) typingUsers[data.name] = true;
        else delete typingUsers[data.name];
        updateTypingIndicator();
    });
    
    socket.on('rooms_list', (roomsData) => {
        const container = document.getElementById('roomsList');
        container.innerHTML = roomsData.map(r => `<div class="room-item ${r === currentRoom ? 'active' : ''}" data-room="${r}">📌 ${escapeHtml(r)}</div>`).join('');
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
        container.innerHTML = usersData.map(u => `<div class="user-item" onclick="startPrivateChat('${escapeHtml(u.name)}')"><span>${u.avatar || '👤'} ${escapeHtml(u.name)}</span> ${u.role === 'owner' ? '<span class="badge-owner">ВЛ</span>' : (u.role === 'admin' ? '<span class="badge-admin">ADM</span>' : (u.role === 'moderator' ? '<span class="badge-moder">МОД</span>' : ''))}</div>`).join('');
    });
    
    socket.on('banned', () => {
        alert('Вы заблокированы!');
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
        const query = prompt('Поиск:');
        if(query) {
            const msgs = document.querySelectorAll('.message-text');
            let found = false;
            msgs.forEach(msg => {
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
    
    let dark = false;
    document.getElementById('themeBtn')?.addEventListener('click', () => {
        dark = !dark;
        document.querySelector('.chat-main').style.background = dark ? '#1f2937' : 'white';
        document.querySelector('.messages-area').style.background = dark ? '#111827' : '#f9fafb';
        document.querySelector('.sidebar').style.background = dark ? '#1f2937' : 'rgba(255,255,255,0.98)';
        document.querySelector('.sidebar').style.color = dark ? 'white' : 'black';
        document.querySelector('.chat-header').style.background = dark ? '#1f2937' : 'white';
        document.querySelector('.chat-header').style.color = dark ? 'white' : 'black';
        document.querySelector('.input-area').style.background = dark ? '#1f2937' : 'white';
    });
    
    document.getElementById('logoutBtn')?.addEventListener('click', () => window.location.href = '/logout');
    
    socket.emit('get_rooms');
    socket.emit('get_users');
</script>
</body>
</html>
'''

# ==================== МАРШРУТЫ ====================
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    user = users.get(session['username'])
    if not user or user.get('banned'):
        session.clear()
        return redirect(url_for('login'))
    role_display = {'owner': 'Владелец', 'admin': 'Администратор', 'moderator': 'Модератор', 'user': 'Пользователь'}.get(user['role'], 'Пользователь')
    return render_template_string(CHAT_PAGE, 
                                 username=session['username'],
                                 role=user['role'],
                                 role_display=role_display,
                                 avatar=user.get('avatar', '👤'))

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
            return render_template_string(REGISTER_PAGE, error='Пароль минимум 4 символа')
        users[username] = {
            'password': hashlib.sha256(password.encode()).hexdigest(),
            'role': 'user',
            'avatar': '👤',
            'banned': False
        }
        save_users(users)
        return redirect(url_for('login'))
    return render_template_string(REGISTER_PAGE, error=None)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==================== SOCKETIO СОБЫТИЯ ====================
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
    text = data
