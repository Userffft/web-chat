from flask import Flask, render_template_string, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import os
import json
import hashlib
import base64

app = Flask(__name__)
app.secret_key = 'chatic-secret-key-2024'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max
socketio = SocketIO(app, cors_allowed_origins="*")

# ==================== ФАЙЛЫ ДАННЫХ ====================
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
            'avatar_base64': None,
            'bio': '👑 Владелец чата',
            'friends': [],
            'friend_requests': [],
            'banned': False,
            'theme': 'light',
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
    return {'Главная': []}

def save_messages(messages):
    with open(MESSAGES_FILE, 'w') as f:
        json.dump(messages, f)

def load_rooms():
    if os.path.exists(ROOMS_FILE):
        with open(ROOMS_FILE, 'r') as f:
            return json.load(f)
    return ['Главная']

def save_rooms(rooms):
    with open(ROOMS_FILE, 'w') as f:
        json.dump(rooms, f)

users = load_users()
messages = load_messages()
rooms = load_rooms()

# ==================== HTML ШАБЛОН ====================
CHAT_HTML = '''
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
            font-family: system-ui, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            transition: all 0.3s;
        }
        body.dark {
            background: #1e1b4b;
        }
        .sidebar {
            width: 280px;
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            border-right: 1px solid rgba(0,0,0,0.1);
            display: flex;
            flex-direction: column;
            padding: 20px;
            transition: all 0.3s;
        }
        body.dark .sidebar {
            background: #1f2937;
            color: white;
        }
        .user-card {
            text-align: center;
            padding: 20px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            border-radius: 24px;
            color: white;
            margin-bottom: 20px;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .user-card:hover { transform: scale(1.02); }
        .user-avatar {
            width: 64px;
            height: 64px;
            border-radius: 50%;
            background: rgba(255,255,255,0.2);
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 10px;
            font-size: 32px;
            overflow: hidden;
        }
        .user-avatar img { width: 100%; height: 100%; object-fit: cover; }
        .user-name { font-size: 18px; font-weight: bold; }
        .user-bio { font-size: 11px; opacity: 0.8; margin-top: 5px; }
        .user-role { font-size: 12px; opacity: 0.9; margin-top: 4px; }
        .section-title { font-weight: 600; margin: 16px 0 8px 0; color: #374151; }
        body.dark .section-title { color: #9ca3af; }
        .room-list, .user-list, .friends-list { list-style: none; }
        .room-item, .user-item, .friend-item {
            padding: 10px 12px;
            border-radius: 12px;
            cursor: pointer;
            margin-bottom: 4px;
            transition: background 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .room-item:hover, .user-item:hover, .friend-item:hover { background: rgba(0,0,0,0.05); }
        .room-item.active { background: #667eea; color: white; }
        .add-room {
            display: flex;
            gap: 8px;
            margin-top: 12px;
        }
        .add-room input {
            flex: 1;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 20px;
            outline: none;
        }
        .add-room button {
            background: #667eea;
            color: white;
            border: none;
            border-radius: 20px;
            padding: 8px 16px;
            cursor: pointer;
        }
        .chat-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: white;
            transition: all 0.3s;
        }
        body.dark .chat-area {
            background: #111827;
        }
        .chat-header {
            padding: 16px 24px;
            border-bottom: 1px solid #eee;
            background: white;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
            align-items: center;
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
        .message-own { justify-content: flex-end; }
        .message-avatar {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            background: #667eea;
            color: white;
            overflow: hidden;
        }
        .message-avatar img { width: 100%; height: 100%; object-fit: cover; }
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
        .message-own .message-content {
            background: #667eea;
            color: white;
        }
        .message-name {
            font-size: 12px;
            font-weight: bold;
            margin-bottom: 4px;
        }
        .message-text { word-wrap: break-word; }
        .message-time {
            font-size: 10px;
            opacity: 0.6;
            margin-left: 8px;
        }
        .system-msg {
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
            background: #667eea;
            border: none;
            border-radius: 50%;
            width: 46px;
            height: 46px;
            color: white;
            cursor: pointer;
        }
        .logout-btn, .settings-btn {
            margin-top: 10px;
            padding: 10px;
            background: #fee2e2;
            border: none;
            border-radius: 20px;
            cursor: pointer;
            color: #dc2626;
            width: 100%;
        }
        .settings-btn {
            background: #e0e7ff;
            color: #4f46e5;
        }
        body.dark .logout-btn {
            background: #374151;
            color: #f87171;
        }
        body.dark .settings-btn {
            background: #374151;
            color: #818cf8;
        }
        .badge-owner { background: #ef4444; font-size: 9px; padding: 2px 6px; border-radius: 12px; margin-left: 6px; }
        .badge-admin { background: #10b981; font-size: 9px; padding: 2px 6px; border-radius: 12px; margin-left: 6px; }
        .online-dot { width: 8px; height: 8px; background: #10b981; border-radius: 50%; display: inline-block; margin-right: 6px; }
        .friend-btn { font-size: 11px; background: rgba(0,0,0,0.1); border: none; border-radius: 16px; padding: 2px 8px; cursor: pointer; margin-left: auto; }
        
        /* Модальное окно */
        .modal {
            display: none;
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.5);
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }
        .modal-content {
            background: white;
            border-radius: 32px;
            padding: 32px;
            max-width: 450px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
        }
        body.dark .modal-content {
            background: #1f2937;
            color: white;
        }
        .modal-content input, .modal-content textarea, .modal-content select {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 24px;
            outline: none;
        }
        body.dark .modal-content input, body.dark .modal-content textarea {
            background: #374151;
            color: white;
            border-color: #4b5563;
        }
        .modal-content button {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px;
            border-radius: 24px;
            width: 100%;
            cursor: pointer;
            margin-top: 10px;
        }
        .close-btn {
            float: right;
            font-size: 24px;
            cursor: pointer;
        }
        .friend-request-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px;
            border-bottom: 1px solid #ddd;
        }
        @media (max-width: 600px) { .sidebar { width: 220px; } }
    </style>
</head>
<body>
<div class="sidebar">
    <div class="user-card" id="profileBtn">
        <div class="user-avatar" id="avatarDisplay">
            {% if avatar_base64 %}
            <img src="{{ avatar_base64 }}">
            {% else %}
            {{ avatar }}
            {% endif %}
        </div>
        <div class="user-name">{{ username }}{% if role == 'owner' %}<span class="badge-owner">ВЛ</span>{% elif role == 'admin' %}<span class="badge-admin">АДМ</span>{% endif %}</div>
        <div class="user-bio">{{ bio }}</div>
        <div class="user-role">{{ role_name }}</div>
    </div>
    <div class="section-title">📌 Комнаты</div>
    <div id="roomsPanel" class="room-list"></div>
    {% if role in ['owner', 'admin'] %}
    <div class="add-room">
        <input type="text" id="newRoomName" placeholder="Название комнаты">
        <button id="createRoomBtn">+</button>
    </div>
    {% endif %}
    <div class="section-title">👥 В чате</div>
    <div id="usersPanel" class="user-list"></div>
    <div class="section-title">👫 Друзья</div>
    <div id="friendsPanel" class="friends-list"></div>
    <button class="settings-btn" id="settingsBtn">⚙️ Настройки</button>
    <button class="logout-btn" id="logoutBtn">🚪 Выйти</button>
</div>
<div class="chat-area">
    <div class="chat-header">
        <span id="currentRoom">Главная</span>
        <span id="onlineCount" style="font-size:12px;">👥 0</span>
    </div>
    <div id="messagesList" class="messages"></div>
    <div id="typingStatus" class="typing"></div>
    <div class="input-area">
        <input type="text" id="messageInput" placeholder="Сообщение...">
        <button id="sendBtn">📤</button>
    </div>
</div>

<!-- Модальное окно профиля -->
<div id="profileModal" class="modal">
    <div class="modal-content">
        <span class="close-btn" id="closeProfileModal">&times;</span>
        <h3>👤 Мой профиль</h3>
        <label>Аватар (эмодзи):</label>
        <input type="text" id="avatarInput" maxlength="2" placeholder="😀">
        <label>Или загрузить изображение:</label>
        <input type="file" id="avatarFileInput" accept="image/jpeg,image/png,image/gif">
        <label>О себе:</label>
        <textarea id="bioInput" rows="3" placeholder="Расскажите о себе..."></textarea>
        <label>Новое имя (3-20 символов):</label>
        <input type="text" id="newNameInput" placeholder="Новое имя">
        <label>Новый пароль (мин. 4 символа):</label>
        <input type="password" id="newPasswordInput" placeholder="Новый пароль">
        <button id="saveProfileBtn">💾 Сохранить</button>
    </div>
</div>

<!-- Модальное окно настроек -->
<div id="settingsModal" class="modal">
    <div class="modal-content">
        <span class="close-btn" id="closeSettingsModal">&times;</span>
        <h3>⚙️ Настройки</h3>
        <label>🌙 Тёмная тема</label>
        <button id="themeToggleBtn" style="background:#e0e7ff; color:#4f46e5;">Переключить тему</button>
        <label>📨 Заявки в друзья</label>
        <div id="friendRequestsList"></div>
        <hr style="margin: 15px 0;">
        <label>👑 Команды (в чате)</label>
        <p style="font-size:12px;">• <code>/giveadmin ИМЯ</code> — выдать админку (владелец)</p>
        <p style="font-size:12px;">• <code>/unadmin ИМЯ</code> — снять админку (владелец)</p>
        <p style="font-size:12px;">• <code>/addfriend ИМЯ</code> — добавить в друзья</p>
        <p style="font-size:12px;">• <code>/acceptfriend ИМЯ</code> — принять заявку</p>
    </div>
</div>

<script>
    let socket = io();
    let currentRoom = 'Главная';
    let username = '{{ username }}';
    let role = '{{ role }}';
    let darkMode = {{ 'true' if user_theme == 'dark' else 'false' }};
    let typingUsers = {};
    let typingTimeout = null;
    
    const messagesDiv = document.getElementById('messagesList');
    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    const typingDiv = document.getElementById('typingStatus');
    const onlineCountSpan = document.getElementById('onlineCount');
    
    function applyTheme() {
        if(darkMode) {
            document.body.classList.add('dark');
        } else {
            document.body.classList.remove('dark');
        }
    }
    applyTheme();
    
    // Модалки
    const profileModal = document.getElementById('profileModal');
    const settingsModal = document.getElementById('settingsModal');
    document.getElementById('profileBtn')?.addEventListener('click', () => {
        document.getElementById('bioInput').value = '{{ bio }}';
        profileModal.style.display = 'flex';
    });
    document.getElementById('settingsBtn')?.addEventListener('click', () => {
        settingsModal.style.display = 'flex';
        loadFriendRequests();
    });
    document.getElementById('closeProfileModal')?.addEventListener('click', () => profileModal.style.display = 'none');
    document.getElementById('closeSettingsModal')?.addEventListener('click', () => settingsModal.style.display = 'none');
    window.onclick = (e) => {
        if(e.target === profileModal) profileModal.style.display = 'none';
        if(e.target === settingsModal) settingsModal.style.display = 'none';
    };
    
    document.getElementById('themeToggleBtn')?.addEventListener('click', () => {
        darkMode = !darkMode;
        applyTheme();
        fetch('/save_theme', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({theme: darkMode ? 'dark' : 'light'})
        });
    });
    
    // Загрузка аватарки
    document.getElementById('avatarFileInput')?.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if(file && (file.type === 'image/jpeg' || file.type === 'image/png' || file.type === 'image/gif')) {
            const reader = new FileReader();
            reader.onload = function(ev) {
                document.getElementById('avatarDisplay').innerHTML = `<img src="${ev.target.result}" style="width:100%;height:100%;object-fit:cover;">`;
                window.tempAvatar = ev.target.result;
            };
            reader.readAsDataURL(file);
        }
    });
    
    // Сохранение профиля
    document.getElementById('saveProfileBtn')?.addEventListener('click', () => {
        const data = {
            avatar_emoji: document.getElementById('avatarInput').value,
            avatar_base64: window.tempAvatar || null,
            bio: document.getElementById('bioInput').value,
            new_name: document.getElementById('newNameInput').value,
            new_password: document.getElementById('newPasswordInput').value
        };
        fetch('/update_profile', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        }).then(res => res.json()).then(data => {
            if(data.success) {
                alert('Профиль обновлён! Страница будет перезагружена.');
                profileModal.style.display = 'none';
                setTimeout(() => location.reload(), 1000);
            } else alert('Ошибка: ' + data.error);
        });
    });
    
    function loadFriendRequests() {
        fetch('/get_friend_requests').then(res => res.json()).then(data => {
            const container = document.getElementById('friendRequestsList');
            if(data.requests && data.requests.length) {
                container.innerHTML = data.requests.map(r => `
                    <div class="friend-request-item">
                        <span>📨 ${escapeHtml(r)}</span>
                        <button onclick="acceptFriend('${escapeHtml(r)}')" style="padding:4px 12px; border-radius:16px; border:none; background:#10b981; color:white;">✓ Принять</button>
                    </div>
                `).join('');
            } else {
                container.innerHTML = '<p style="color:#6b7280;">Нет заявок</p>';
            }
        });
    }
    
    window.acceptFriend = function(name) {
        fetch('/accept_friend', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({friend: name})
        }).then(res => res.json()).then(data => {
            alert(data.message);
            loadFriendRequests();
            socket.emit('get_users');
        });
    };
    
    function addMessage(name, text, time, isOwn, avatar, avatarBase64) {
        let div = document.createElement('div');
        div.className = `message ${isOwn ? 'message-own' : ''}`;
        let avatarHtml = '';
        if(avatarBase64) {
            avatarHtml = `<img src="${avatarBase64}" style="width:100%;height:100%;object-fit:cover;">`;
        } else {
            avatarHtml = avatar || '👤';
        }
        div.innerHTML = `
            <div class="message-avatar" onclick="showUserProfile('${escapeHtml(name)}')">${avatarHtml}</div>
            <div class="message-content">
                <div class="message-name">${escapeHtml(name)}<span class="message-time">${time}</span></div>
                <div class="message-text">${escapeHtml(text)}</div>
            </div>
        `;
        messagesDiv.appendChild(div);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    
    window.showUserProfile = function(name) {
        fetch('/get_user_info/' + encodeURIComponent(name)).then(res => res.json()).then(data => {
            alert(`${data.username}\n📝 ${data.bio || 'Нет описания'}\n👫 Друзья: ${data.friends_count || 0}\n⭐ Роль: ${data.role_display}`);
        });
    };
    
    function addSystemMessage(text) {
        let div = document.createElement('div');
        div.className = 'system-msg';
        div.textContent = text;
        messagesDiv.appendChild(div);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    
    function escapeHtml(str) {
        return str.replace(/[&<>]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;'})[m]);
    }
    
    socket.emit('join', { room: currentRoom });
    
    socket.on('history', (history) => {
        messagesDiv.innerHTML = '';
        history.forEach(msg => addMessage(msg.name, msg.text, msg.time, msg.name === username, msg.avatar, msg.avatar_base64));
    });
    
    socket.on('new_message', (msg) => {
        addMessage(msg.name, msg.text, msg.time, msg.name === username, msg.avatar, msg.avatar_base64);
        if(msg.name !== username && !document.hasFocus()) {
            document.title = '🔔 Новое сообщение';
            setTimeout(() => { if(document.title === '🔔 Новое сообщение') document.title = 'Чатик'; }, 2000);
        }
    });
    
    socket.on('system_message', (data) => addSystemMessage(data.text));
    
    socket.on('rooms_update', (roomsList) => {
        const container = document.getElementById('roomsPanel');
        container.innerHTML = roomsList.map(r => `<div class="room-item ${r === currentRoom ? 'active' : ''}" data-room="${r}">🏠 ${escapeHtml(r)}</div>`).join('');
        document.querySelectorAll('.room-item').forEach(el => {
            el.onclick = () => {
                let newRoom = el.dataset.room;
                if(newRoom === currentRoom) return;
                socket.emit('switch_room', { old_room: currentRoom, new_room: newRoom });
                currentRoom = newRoom;
                document.getElementById('currentRoom').innerText = currentRoom;
                document.querySelectorAll('.room-item').forEach(i => i.classList.remove('active'));
                el.classList.add('active');
                messagesDiv.innerHTML = '<div class="system-msg">⏳ Загрузка...</div>';
            };
        });
    });
    
    socket.on('users_update', (usersList) => {
        const container = document.getElementById('usersPanel');
        container.innerHTML = usersList.map(u => `
            <div class="user-item" onclick="showUserProfile('${escapeHtml(u.name)}')">
                <span class="online-dot"></span>
                <div class="message-avatar" style="width:24px;height:24px; font-size:12px;">${u.avatar_base64 ? `<img src="${u.avatar_base64}" style="width:100%;height:100%;">` : (u.avatar || '👤')}</div>
                ${escapeHtml(u.name)} ${u.role === 'owner' ? '<span class="badge-owner">ВЛ</span>' : (u.role === 'admin' ? '<span class="badge-admin">АДМ</span>' : '')}
                ${!u.is_friend && u.name !== username ? `<button class="friend-btn" onclick="event.stopPropagation(); addFriend('${escapeHtml(u.name)}')">+ Друг</button>` : ''}
                ${u.is_friend ? '<span style="font-size:10px; margin-left:auto;">✓ Друг</span>' : ''}
            </div>
        `).join('');
        onlineCountSpan.innerText = `👥 ${usersList.length}`;
    });
    
    window.addFriend = function(name) {
        fetch('/add_friend', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({friend: name})
        }).then(res => res.json()).then(data => {
            addSystemMessage(data.message);
        });
    };
    
    socket.on('friends_update', (friendsList) => {
        const container = document.getElementById('friendsPanel');
        if(!container) return;
        container.innerHTML = friendsList.map(f => `<div class="friend-item" onclick="showUserProfile('${escapeHtml(f.name)}')">👫 ${escapeHtml(f.name)}</div>`).join('');
        if(friendsList.length === 0) container.innerHTML = '<div class="friend-item" style="color:#6b7280;">Нет друзей</div>';
    });
    
    socket.on('typing_status', (data) => {
        if(data.typing) typingUsers[data.name] = true;
        else delete typingUsers[data.name];
        let names = Object.keys(typingUsers).filter(n => n !== username);
        typingDiv.innerText = names.length ? (names.length === 1 ? `${names[0]} печатает...` : `${names.length} человек печатают...`) : '';
    });
    
    sendBtn.onclick = () => {
        let text = messageInput.value.trim();
        if(text) {
            if(text.startsWith('/giveadmin ') && role === 'owner') {
                let target = text.split(' ')[1];
                fetch('/give_admin', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username: target})})
                    .then(res => res.json()).then(data => addSystemMessage(data.message));
                messageInput.value = '';
                return;
            }
            if(text.startsWith('/unadmin ') && role === 'owner') {
                let target = text.split(' ')[1];
                fetch('/remove_admin', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username: target})})
                    .then(res => res.json()).then(data => addSystemMessage(data.message));
                messageInput.value = '';
                return;
            }
            if(text.startsWith('/addfriend ')) {
                let target = text.split(' ')[1];
                fetch('/add_friend', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({friend: target})})
                    .then(res => res.json()).then(data => addSystemMessage(data.message));
                messageInput.value = '';
                return;
            }
            if(text.startsWith('/acceptfriend ')) {
                let target = text.split(' ')[1];
                fetch('/accept_friend', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({friend: target})})
                    .then(res => res.json()).then(data => addSystemMessage(data.message));
                messageInput.value = '';
                return;
            }
            socket.emit('send_message', { text: text, room: currentRoom });
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
        let newRoom = document.getElementById('newRoomName').value.trim();
        if(newRoom) {
            socket.emit('create_room', { room: newRoom });
            document.getElementById('newRoomName').value = '';
        }
    });
    
    document.getElementById('logoutBtn')?.addEventListener('click', () => window.location.href = '/logout');
    
    socket.emit('get_rooms');
    socket.emit('get_users');
</script>
</body>
</html>
'''

LOGIN_PAGE = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Вход</title><style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center}.card{background:white;border-radius:48px;padding:48px;max-width:400px;width:100%;text-align:center}h1{margin-bottom:8px;background:linear-gradient(135deg,#667eea,#764ba2);-webkit-background-clip:text;-webkit-text-fill-color:transparent}.subtitle{color:#6b7280;margin-bottom:32px}input{width:100%;padding:16px;border:2px solid #e5e7eb;border-radius:32px;margin-bottom:16px}button{width:100%;padding:16px;background:#667eea;color:white;border:none;border-radius:32px;cursor:pointer}.error{background:#fee2e2;color:#dc2626;padding:12px;border-radius:24px;margin-bottom:20px}.footer{margin-top:24px}a{color:#667eea}
</style></head>
<body><div class="card"><h1>💬 Чатик</h1><div class="subtitle">Общайся с друзьями</div>{% if error %}<div class="error">{{ error }}</div>{% endif %}<form method="post"><input type="text" name="username" placeholder="Имя" required autofocus><input type="password" name="password" placeholder="Пароль" required><button type="submit">Войти</button></form><div class="footer">Нет аккаунта? <a href="/register">Регистрация</a></div></div></body>
</html>'''

REGISTER_PAGE = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Регистрация</title><style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center}.card{background:white;border-radius:48px;padding:48px;max-width:400px;width:100%}h1{text-align:center;margin-bottom:32px;background:linear-gradient(135deg,#667eea,#764ba2);-webkit-background-clip:text;-webkit-text-fill-color:transparent}input{width:100%;padding:16px;border:2px solid #e5e7eb;border-radius:32px;margin-bottom:16px}button{width:100%;padding:16px;background:#667eea;color:white;border:none;border-radius:32px;cursor:pointer}.error{background:#fee2e2;color:#dc2626;padding:12px;border-radius:24px;margin-bottom:20px}.footer{text-align:center;margin-top:24px}a{color:#667eea}
</style></head>
<body><div class="card"><h1>📝 Регистрация</h1>{% if error %}<div class="error">{{ error }}</div>{% endif %}<form method="post"><input type="text" name="username" placeholder="Имя (3-20 символов)" required autofocus><input type="password" name="password" placeholder="Пароль (мин. 4)" required><button type="submit">Создать аккаунт</button></form><div class="footer">Уже есть аккаунт? <a href="/login">Войти</a></div></div></body>
</html>'''

# ==================== МАРШРУТЫ ====================
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    user = users.get(session['username'])
    if not user or user.get('banned'):
        session.clear()
        return redirect(url_for('login'))
    role_name = {'owner': 'Владелец', 'admin': 'Админ', 'moderator': 'Модератор', 'user': 'Пользователь'}.get
