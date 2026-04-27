from flask import Flask, render_template_string, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import os
import json
import hashlib

app = Flask(__name__)
app.secret_key = 'secret-key-2024'
socketio = SocketIO(app, cors_allowed_origins="*")

# ==================== ДАННЫЕ ====================
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
            'bio': 'Владелец чата',
            'friends': [],
            'requests': [],
            'banned': False,
            'theme': 'light'
        },
        'dimooon': {
            'password': hashlib.sha256('1111'.encode()).hexdigest(),
            'role': 'admin',
            'avatar': '😎',
            'bio': 'Главный админ',
            'friends': [],
            'requests': [],
            'banned': False,
            'theme': 'light'
        }
    }

def save_users(u):
    with open(USERS_FILE, 'w') as f:
        json.dump(u, f)

def load_messages():
    if os.path.exists(MESSAGES_FILE):
        with open(MESSAGES_FILE, 'r') as f:
            return json.load(f)
    return {'Главная': []}

def save_messages(m):
    with open(MESSAGES_FILE, 'w') as f:
        json.dump(m, f)

def load_rooms():
    if os.path.exists(ROOMS_FILE):
        with open(ROOMS_FILE, 'r') as f:
            return json.load(f)
    return ['Главная', 'Случайная', 'Помощь']

def save_rooms(r):
    with open(ROOMS_FILE, 'w') as f:
        json.dump(r, f)

users = load_users()
messages = load_messages()
rooms = load_rooms()

# ==================== ШАБЛОНЫ ====================
LOGIN_HTML = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Чатик · Вход</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}.card{background:rgba(255,255,255,0.95);backdrop-filter:blur(10px);border-radius:48px;padding:48px;max-width:400px;width:100%;text-align:center;box-shadow:0 25px 50px -12px rgba(0,0,0,0.25)}h1{margin-bottom:8px;background:linear-gradient(135deg,#667eea,#764ba2);-webkit-background-clip:text;-webkit-text-fill-color:transparent}.subtitle{color:#6b7280;margin-bottom:32px}input{width:100%;padding:16px;border:2px solid #e5e7eb;border-radius:32px;margin-bottom:16px;font-size:16px;outline:none}input:focus{border-color:#667eea;box-shadow:0 0 0 3px rgba(102,126,234,0.1)}button{width:100%;padding:16px;background:linear-gradient(135deg,#667eea,#764ba2);color:white;border:none;border-radius:32px;font-size:16px;font-weight:600;cursor:pointer;transition:transform 0.2s}button:hover{transform:translateY(-2px)}.error{background:#fee2e2;color:#dc2626;padding:12px;border-radius:24px;margin-bottom:20px}.footer{margin-top:24px;color:#6b7280}a{color:#667eea;text-decoration:none}
</style>
</head>
<body><div class="card"><h1>💬 Чатик</h1><div class="subtitle">Общайся с друзьями</div>{% if error %}<div class="error">{{ error }}</div>{% endif %}<form method="post"><input type="text" name="username" placeholder="Имя пользователя" required autofocus><input type="password" name="password" placeholder="Пароль" required><button type="submit">Войти</button></form><div class="footer">Нет аккаунта? <a href="/register">Зарегистрироваться</a></div></div></body>
</html>
'''

REGISTER_HTML = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Чатик · Регистрация</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}.card{background:rgba(255,255,255,0.95);backdrop-filter:blur(10px);border-radius:48px;padding:48px;max-width:400px;width:100%;text-align:center;box-shadow:0 25px 50px -12px rgba(0,0,0,0.25)}h1{text-align:center;margin-bottom:32px;background:linear-gradient(135deg,#667eea,#764ba2);-webkit-background-clip:text;-webkit-text-fill-color:transparent}input{width:100%;padding:16px;border:2px solid #e5e7eb;border-radius:32px;margin-bottom:16px;font-size:16px;outline:none}input:focus{border-color:#667eea;box-shadow:0 0 0 3px rgba(102,126,234,0.1)}button{width:100%;padding:16px;background:linear-gradient(135deg,#667eea,#764ba2);color:white;border:none;border-radius:32px;font-size:16px;font-weight:600;cursor:pointer;transition:transform 0.2s}button:hover{transform:translateY(-2px)}.error{background:#fee2e2;color:#dc2626;padding:12px;border-radius:24px;margin-bottom:20px;text-align:center}.footer{text-align:center;margin-top:24px;color:#6b7280}a{color:#667eea;text-decoration:none}
</style>
</head>
<body><div class="card"><h1>📝 Регистрация</h1>{% if error %}<div class="error">{{ error }}</div>{% endif %}<form method="post"><input type="text" name="username" placeholder="Имя (3-20 символов)" required autofocus><input type="password" name="password" placeholder="Пароль (мин. 4)" required><button type="submit">Создать аккаунт</button></form><div class="footer">Уже есть аккаунт? <a href="/login">Войти</a></div></div></body>
</html>
'''

CHAT_HTML = '''
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>Чатик · {{ username }}</title>
<script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:linear-gradient(135deg,#1e1b4b,#4c1d95);height:100vh;display:flex;transition:0.3s}body.dark{background:#0f172a}.sidebar{width:280px;background:rgba(255,255,255,0.95);backdrop-filter:blur(10px);border-right:1px solid rgba(0,0,0,0.1);display:flex;flex-direction:column;overflow-y:auto}body.dark .sidebar{background:#1e293b;color:#fff}.user-card{text-align:center;padding:24px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;cursor:pointer}.user-avatar{font-size:64px}.user-name{font-size:18px;font-weight:700}.user-bio{font-size:12px;opacity:0.85;margin-top:5px}.section-title{font-weight:600;padding:16px 20px 8px 20px;color:#475569;font-size:13px;text-transform:uppercase;letter-spacing:0.5px}body.dark .section-title{color:#94a3b8}.room-item,.user-item{padding:12px 20px;margin:4px 12px;border-radius:16px;cursor:pointer;display:flex;align-items:center;gap:12px;transition:all 0.2s}.room-item:hover,.user-item:hover{background:rgba(0,0,0,0.05)}body.dark .room-item:hover,body.dark .user-item:hover{background:rgba(255,255,255,0.05)}.room-item.active{background:#4f46e5;color:#fff}.add-room{display:flex;gap:8px;margin:12px}.add-room input{flex:1;padding:10px 16px;border:1px solid #e2e8f0;border-radius:40px;outline:none}body.dark .add-room input{background:#334155;color:#fff;border-color:#475569}.add-room button{background:#4f46e5;color:#fff;border:none;border-radius:40px;padding:8px 20px;cursor:pointer}.chat-area{flex:1;display:flex;flex-direction:column;background:#fff}body.dark .chat-area{background:#0f172a}.chat-header{padding:20px 24px;background:#fff;border-bottom:1px solid #e2e8f0;display:flex;justify-content:space-between;align-items:center}body.dark .chat-header{background:#1e293b;color:#fff;border-color:#334155}.messages{flex:1;overflow-y:auto;padding:24px;display:flex;flex-direction:column;gap:16px}.message{display:flex;gap:12px;align-items:flex-start;animation:fadeIn 0.2s ease}@keyframes fadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}.message-own{justify-content:flex-end}.message-avatar{width:40px;height:40px;background:linear-gradient(135deg,#667eea,#764ba2);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:20px;cursor:pointer}.message-content{background:#f1f5f9;padding:10px 16px;border-radius:20px;max-width:65%;border-bottom-left-radius:4px}body.dark .message-content{background:#334155;color:#fff}.message-own .message-content{background:#4f46e5;color:#fff;border-bottom-right-radius:4px;border-bottom-left-radius:20px}.message-name{font-weight:700;font-size:13px;display:flex;align-items:center;gap:6px;flex-wrap:wrap}.message-time{font-size:10px;opacity:0.6;margin-left:8px}.message-text{margin-top:4px;font-size:14px;word-wrap:break-word}.badge-owner{background:#ef4444;font-size:9px;padding:2px 8px;border-radius:20px;margin-left:6px}.badge-admin{background:#10b981;font-size:9px;padding:2px 8px;border-radius:20px;margin-left:6px}.online-dot{width:10px;height:10px;background:#10b981;border-radius:50%;display:inline-block;margin-right:8px}.system-msg{text-align:center;font-size:12px;color:#64748b;padding:8px;margin:8px 0}.typing-indicator{padding:8px 24px;font-size:12px;color:#64748b;font-style:italic}.input-area{display:flex;gap:12px;padding:20px 24px;background:#fff;border-top:1px solid #e2e8f0}body.dark .input-area{background:#1e293b;border-color:#334155}.input-area input{flex:1;padding:14px 20px;border:2px solid #e2e8f0;border-radius:40px;outline:none;font-size:14px}body.dark .input-area input{background:#334155;color:#fff;border-color:#475569}.input-area button{background:#4f46e5;border:none;border-radius:50%;width:48px;height:48px;color:#fff;cursor:pointer;font-size:18px;transition:transform 0.2s}.input-area button:hover{transform:scale(1.05)}.btn-settings,.btn-logout{margin:8px 12px;padding:12px;border-radius:20px;cursor:pointer;font-weight:500;border:none}.btn-settings{background:#e0e7ff;color:#4f46e5}.btn-logout{background:#fee2e2;color:#dc2626}body.dark .btn-settings{background:#334155;color:#818cf8}body.dark .btn-logout{background:#334155;color:#f87171}.modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);align-items:center;justify-content:center;z-index:1000}.modal-content{background:#fff;border-radius:32px;padding:32px;max-width:400px;width:90%;max-height:80vh;overflow-y:auto}body.dark .modal-content{background:#1e293b;color:#fff}.modal-content input,.modal-content textarea{width:100%;padding:12px;margin:10px 0;border:1px solid #e2e8f0;border-radius:24px;outline:none}body.dark .modal-content input,body.dark .modal-content textarea{background:#334155;border-color:#475569;color:#fff}.modal-content button{background:#4f46e5;color:#fff;border:none;padding:12px;border-radius:24px;width:100%;cursor:pointer;margin-top:10px}.close{float:right;font-size:28px;cursor:pointer;line-height:20px}.user-menu{position:fixed;background:#fff;border-radius:16px;box-shadow:0 10px 25px rgba(0,0,0,0.1);padding:8px;z-index:1000;display:none;min-width:160px}body.dark .user-menu{background:#1e293b;box-shadow:0 10px 25px rgba(0,0,0,0.3)}.user-menu button{width:100%;padding:10px 16px;border:none;background:none;text-align:left;cursor:pointer;border-radius:12px;font-size:14px}.user-menu button:hover{background:#f1f5f9}body.dark .user-menu button:hover{background:#334155;color:#fff}.emoji-picker{position:absolute;bottom:80px;left:20px;background:#fff;border-radius:20px;padding:12px;display:none;grid-template-columns:repeat(6,1fr);gap:8px;box-shadow:0 10px 25px rgba(0,0,0,0.1);z-index:1000}body.dark .emoji-picker{background:#1e293b}.emoji{font-size:24px;cursor:pointer;text-align:center;padding:5px;border-radius:12px}.emoji:hover{background:#f1f5f9}body.dark .emoji:hover{background:#334155}@media(max-width:680px){.sidebar{width:260px}}
</style>
</head>
<body>
<div class="sidebar">
    <div class="user-card" id="profileBtn">
        <div class="user-avatar">{{ avatar }}</div>
        <div class="user-name">{{ username }}{% if role == 'owner' %}<span class="badge-owner"> ВЛ</span>{% elif role == 'admin' %}<span class="badge-admin"> АДМ</span>{% endif %}</div>
        <div class="user-bio">{{ bio[:50] }}</div>
    </div>
    <div class="section-title">🏠 КОМНАТЫ</div>
    <div id="roomsList"></div>
    {% if role in ['owner', 'admin'] %}
    <div class="add-room"><input type="text" id="newRoom" placeholder="Название комнаты"><button id="createRoomBtn">+</button></div>
    {% endif %}
    <div class="section-title">👥 ОНЛАЙН</div>
    <div id="usersList"></div>
    <div class="section-title">👫 ДРУЗЬЯ</div>
    <div id="friendsList"></div>
    <button class="btn-settings" id="settingsBtn">⚙️ Настройки</button>
    <button class="btn-logout" id="logoutBtn">🚪 Выйти</button>
</div>
<div class="chat-area">
    <div class="chat-header">
        <span><strong>#</strong> <span id="roomName">Главная</span></span>
        <span id="onlineCount" style="font-size:13px;">👥 0</span>
    </div>
    <div id="messagesList" class="messages"></div>
    <div id="typingStatus" class="typing-indicator"></div>
    <div class="input-area">
        <button id="emojiBtn">😊</button>
        <input type="text" id="messageInput" placeholder="Сообщение...">
        <button id="sendBtn">📤</button>
    </div>
</div>

<div id="emojiPicker" class="emoji-picker"></div>

<div id="profileModal" class="modal"><div class="modal-content">
    <span class="close" id="closeProfile">&times;</span>
    <h3>👤 Мой профиль</h3>
    <label>Аватар (эмодзи):</label><input type="text" id="avatarInput" maxlength="2" placeholder="😀">
    <label>О себе:</label><textarea id="bioInput" rows="3" placeholder="Расскажите о себе...">{{ bio }}</textarea>
    <label>Новое имя:</label><input type="text" id="newName" placeholder="Новое имя">
    <label>Новый пароль:</label><input type="password" id="newPass" placeholder="Новый пароль">
    <button id="saveProfile">💾 Сохранить</button>
</div></div>

<div id="settingsModal" class="modal"><div class="modal-content">
    <span class="close" id="closeSettings">&times;</span>
    <h3>⚙️ Настройки</h3>
    <button id="themeBtn" style="background:#e0e7ff;">🌙 Тёмная тема</button>
    <h4 style="margin-top:20px;">📨 Заявки в друзья</h4><div id="requestsList"></div>
    <h4 style="margin-top:20px;">👑 Команды</h4>
    <p style="font-size:12px;">• <code>/giveadmin ИМЯ</code> — выдать админку</p>
    <p style="font-size:12px;">• <code>/unadmin ИМЯ</code> — снять админку</p>
</div></div>

<div id="userMenu" class="user-menu"></div>

<script>
let socket = io();
let currentRoom = 'Главная';
let username = '{{ username }}';
let role = '{{ role }}';
let darkMode = false;
let typingUsers = {};
let currentMenuUser = null;

const msgDiv = document.getElementById('messagesList');
const msgInput = document.getElementById('messageInput');

// Эмодзи-пикер
const emojis = ['😀','😂','❤️','👍','🎉','🔥','😍','🥹','😭','🤔','👋','🙏','✨','💯','😎','🥳','😡','🤯','🥰','😱'];
const picker = document.getElementById('emojiPicker');
if(picker) {
    picker.innerHTML = emojis.map(e => `<div class="emoji">${e}</div>`).join('');
    document.querySelectorAll('.emoji').forEach(el => {
        el.onclick = () => {
            msgInput.value += el.textContent;
            msgInput.focus();
            picker.style.display = 'none';
        };
    });
    document.getElementById('emojiBtn').onclick = () => {
        picker.style.display = picker.style.display === 'grid' ? 'none' : 'grid';
    };
    document.addEventListener('click', (e) => {
        if(!e.target.closest('#emojiBtn') && !e.target.closest('.emoji-picker')) {
            picker.style.display = 'none';
        }
        if(!e.target.closest('.user-item') && !e.target.closest('.user-menu')) {
            document.getElementById('userMenu').style.display = 'none';
            currentMenuUser = null;
        }
    });
}

function showUserMenu(name, x, y) {
    let menu = document.getElementById('userMenu');
    if(currentMenuUser === name && menu.style.display === 'block') {
        menu.style.display = 'none';
        currentMenuUser = null;
        return;
    }
    fetch('/user_info/' + encodeURIComponent(name)).then(r => r.json()).then(data => {
        menu.innerHTML = `
            <button onclick="viewProfile('${name}')">👤 Просмотр профиля</button>
            ${!data.is_friend && name !== username ? `<button onclick="addFriend('${name}')">➕ В друзья</button>` : ''}
            ${data.is_friend ? `<button onclick="removeFriend('${name}')">❌ Удалить из друзей</button>` : ''}
            ${(role === 'owner' || role === 'admin') ? `<button onclick="giveAdmin('${name}')">⭐ Выдать админку</button>` : ''}
        `;
        menu.style.display = 'block';
        menu.style.left = x + 'px';
        menu.style.top = y + 'px';
        currentMenuUser = name;
        setTimeout(() => {
            if(menu.style.display === 'block') {
                menu.style.display = 'none';
                currentMenuUser = null;
            }
        }, 5000);
    });
}

window.viewProfile = function(name) {
    fetch('/user_info/' + encodeURIComponent(name)).then(r => r.json()).then(data => {
        alert(`${data.username}\n📝 ${data.bio || 'Нет описания'}\n👫 Друзья: ${data.friends_count}\n⭐ Роль: ${data.role_display}`);
    });
    document.getElementById('userMenu').style.display = 'none';
};

window.addFriend = function(name) {
    fetch('/add_friend', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({friend:name})})
        .then(r => r.json()).then(data => addSystemMessage(data.message));
    document.getElementById('userMenu').style.display = 'none';
};

window.removeFriend = function(name) {
    fetch('/remove_friend', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({friend:name})})
        .then(r => r.json()).then(data => addSystemMessage(data.message));
    document.getElementById('userMenu').style.display = 'none';
};

window.giveAdmin = function(name) {
    fetch('/give_admin', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:name})})
        .then(r => r.json()).then(data => addSystemMessage(data.message));
    document.getElementById('userMenu').style.display = 'none';
};

function loadRequests() {
    fetch('/get_requests').then(r => r.json()).then(data => {
        let div = document.getElementById('requestsList');
        if(data.requests && data.requests.length) {
            div.innerHTML = data.requests.map(r => `<div style="display:flex;justify-content:space-between;margin:8px 0;"><span>📨 ${escape(r)}</span><button onclick="acceptReq('${escape(r)}')" style="background:#10b981;border:none;border-radius:16px;padding:4px 12px;color:#fff;">Принять</button></div>`).join('');
        } else div.innerHTML = '<p>Нет заявок</p>';
    });
}

window.acceptReq = function(name) {
    fetch('/accept_friend', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({friend:name})})
        .then(r => r.json()).then(data => { addSystemMessage(data.message); loadRequests(); });
};

function addMessage(id, name, text, time, isOwn, avatar) {
    let div = document.createElement('div');
    div.className = `message ${isOwn ? 'message-own' : ''}`;
    div.innerHTML = `<div class="message-avatar">${avatar || '👤'}</div><div class="message-content"><div class="message-name">${escape(name)}<span class="message-time">${time}</span></div><div class="message-text">${escape(text)}</div></div>`;
    msgDiv.appendChild(div);
    msgDiv.scrollTop = msgDiv.scrollHeight;
}

function addSystemMessage(text) {
    let div = document.createElement('div');
    div.className = 'system-msg';
    div.textContent = text;
    msgDiv.appendChild(div);
    msgDiv.scrollTop = msgDiv.scrollHeight;
}

function escape(str) {
    return str.replace(/[&<>]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;'})[m]);
}

socket.emit('join', { room: currentRoom });

socket.on('history', (data) => {
    msgDiv.innerHTML = '';
    data.forEach(m => addMessage(m.id, m.name, m.text, m.time, m.name === username, m.avatar));
});

socket.on('message', (m) => {
    addMessage(m.id, m.name, m.text, m.time, m.name === username, m.avatar);
});

socket.on('system', (data) => addSystemMessage(data.text));

socket.on('rooms', (list) => {
    let container = document.getElementById('roomsList');
    container.innerHTML = list.map(r => `<div class="room-item ${r === currentRoom ? 'active' : ''}" data-room="${r}">🏠 ${escape(r)}</div>`).join('');
    document.querySelectorAll('.room-item').forEach(el => {
        el.onclick = () => {
            let newRoom = el.dataset.room;
            if(newRoom === currentRoom) return;
            socket.emit('switch', { old: currentRoom, new: newRoom });
            currentRoom = newRoom;
            document.getElementById('roomName').innerText = currentRoom;
            document.querySelectorAll('.room-item').forEach(i => i.classList.remove('active'));
            el.classList.add('active');
            msgDiv.innerHTML = '<div class="system-msg">⏳ Загрузка...</div>';
        };
    });
});

socket.on('users', (list) => {
    let container = document.getElementById('usersList');
    container.innerHTML = list.map(u => `<div class="user-item" data-user="${escape(u.name)}" onclick="showUserMenu('${escape(u.name)}', event.clientX, event.clientY)"><span class="online-dot"></span> ${u.avatar || '👤'} ${escape(u.name)} ${u.role === 'owner' ? '<span class="badge-owner">ВЛ</span>' : (u.role === 'admin' ? '<span class="badge-admin">АДМ</span>' : '')}</div>`).join('');
    document.getElementById('onlineCount').innerText = `👥 ${list.length}`;
});

socket.on('friends', (list) => {
    let container = document.getElementById('friendsList');
    if(container) container.innerHTML = list.map(f => `<div class="user-item" onclick="viewProfile('${escape(f.name)}')">👫 ${escape(f.name)}</div>`).join('');
});

socket.on('typing', (data) => {
    if(data.typing) typingUsers[data.name] = true;
    else delete typingUsers[data.name];
    let names = Object.keys(typingUsers).filter(n => n !== username);
    document.getElementById('typingStatus').innerText = names.length ? (names.length === 1 ? `${names[0]} печатает...` : `${names.length} человек печатают...`) : '';
});

document.getElementById('sendBtn').onclick = () => {
    let text = msgInput.value.trim();
    if(!text) return;
    if(text.startsWith('/giveadmin ') && role === 'owner') {
        let target = text.split(' ')[1];
        fetch('/give_admin', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:target})})
            .then(r => r.json()).then(data => addSystemMessage(data.message));
        msgInput.value = '';
        return;
    }
    if(text.startsWith('/unadmin ') && role === 'owner') {
        let target = text.split(' ')[1];
        fetch('/remove_admin', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:target})})
            .then(r => r.json()).then(data => addSystemMessage(data.message));
        msgInput.value = '';
        return;
    }
    socket.emit('message', { text: text, room: currentRoom });
    msgInput.value = '';
};

msgInput.onkeypress = (e) => {
    if(e.key === 'Enter') document.getElementById('sendBtn').click();
    socket.emit('typing', { room: currentRoom, typing: true });
    clearTimeout(window.typingTimeout);
    window.typingTimeout = setTimeout(() => socket.emit('typing', { room: currentRoom, typing: false }), 1000);
};

document.getElementById('createRoomBtn')?.addEventListener('click', () => {
    let name = document.getElementById('newRoom').value.trim();
    if(name) {
        socket.emit('create', { room: name });
        document.getElementById('newRoom').value = '';
    }
});

document.getElementById('profileBtn').onclick = () => document.getElementById('profileModal').style.display = 'flex';
document.getElementById('settingsBtn').onclick = () => {
    document.getElementById('settingsModal').style.display = 'flex';
    loadRequests();
};
document.getElementById('closeProfile').onclick = () => document.getElementById('profileModal').style.display = 'none';
document.getElementById('closeSettings').onclick = () => document.getElementById('settingsModal').style.display = 'none';
window.onclick = (e) => {
    if(e.target === document.getElementById('profileModal')) document.getElementById('profileModal').style.display = 'none';
    if(e.target === document.getElementById('settingsModal')) document.getElementById('settingsModal').style.display = 'none';
};

document.getElementById('saveProfile').onclick = () => {
    fetch('/update_profile', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
        avatar: document.getElementById('avatarInput').value,
        bio: document.getElementById('bioInput').value,
        new_name: document.getElementById('newName').value,
        new_password: document.getElementById('newPass').value
    })}).then(r => r.json()).then(data => {
        if(data.success) {
            alert('Сохранено! Страница перезагрузится.');
            location.reload();
        } else alert('Ошибка: ' + data.error);
    });
};

document.getElementById('themeBtn').onclick = () => {
    darkMode = !darkMode;
    if(darkMode) document.body.classList.add('dark');
    else document.body.classList.remove('dark');
    fetch('/save_theme', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({theme: darkMode ? 'dark' : 'light'})});
};

document.getElementById('logoutBtn').onclick = () => window.location.href = '/logout';

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
    u = users.get(session['username'])
    if not u or u.get('banned'):
        session.clear()
        return redirect(url_for('login'))
    role_names = {'owner': 'Владелец', 'admin': 'Админ', 'moderator': 'Модератор', 'user': 'Пользователь'}
    return render_template_string(CHAT_HTML, 
        username=session['username'],
        role=u['role'],
        role_name=role_names.get(u['role'], 'Пользователь'),
        avatar=u.get('avatar', '👤'),
        bio=u.get('bio', '')
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['username']
        pwd = request.form['password']
        h = hashlib.sha256(pwd.encode()).hexdigest()
        if name in users and users[name]['password'] == h:
            if users[name].get('banned'):
                return render_template_string(LOGIN_HTML, error='Вы заблокированы')
            session['username'] = name
            return redirect(url_for('index'))
        return render_template_string(LOGIN_HTML, error='Неверные данные')
    return render_template_string(LOGIN_HTML)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['username']
        pwd = request.form['password']
        if name in users:
            return render_template_string(REGISTER_HTML, error='Имя занято')
        if len(name) < 3 or len(name) > 20:
            return render_template_string(REGISTER_HTML, error='Имя 3-20 символов')
        if len(pwd) < 4:
            return render_template_string(REGISTER_HTML, error='Пароль минимум 4 символа')
        users[name] = {
            'password': hashlib.sha256(pwd
