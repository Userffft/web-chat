from flask import Flask, render_template_string, request, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import os
import json
import hashlib

app = Flask(__name__)
app.secret_key = 'chatic-secret-key-2024'
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
            'theme': 'light',
            'created_at': datetime.now().isoformat()
        },
        'dimooon': {
            'password': hashlib.sha256('1111'.encode()).hexdigest(),
            'role': 'admin',
            'avatar': '😎',
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
        .user-avatar { font-size: 48px; margin-bottom: 8px; }
        .user-name { font-size: 18px; font-weight: bold; }
        .user-role { font-size: 12px; opacity: 0.9; margin-top: 4px; }
        .section-title { font-weight: 600; margin: 16px 0 8px 0; color: #374151; }
        body.dark .section-title { color: #9ca3af; }
        .room-list, .user-list { list-style: none; }
        .room-item, .user-item {
            padding: 10px 12px;
            border-radius: 12px;
            cursor: pointer;
            margin-bottom: 4px;
            transition: background 0.2s;
        }
        .room-item:hover, .user-item:hover { background: rgba(0,0,0,0.05); }
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
            background: #667eea;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 14px;
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
        .logout-btn {
            margin-top: 20px;
            padding: 10px;
            background: #fee2e2;
            border: none;
            border-radius: 20px;
            cursor: pointer;
            color: #dc2626;
        }
        body.dark .logout-btn {
            background: #374151;
            color: #f87171;
        }
        .badge-owner { background: #ef4444; font-size: 9px; padding: 2px 6px; border-radius: 12px; margin-left: 6px; }
        .badge-admin { background: #10b981; font-size: 9px; padding: 2px 6px; border-radius: 12px; margin-left: 6px; }
        
        /* Модальное окно профиля */
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
            max-width: 400px;
            width: 90%;
        }
        body.dark .modal-content {
            background: #1f2937;
            color: white;
        }
        .modal-content input, .modal-content select {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 24px;
            outline: none;
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
        @media (max-width: 600px) { .sidebar { width: 220px; } }
    </style>
</head>
<body>
<div class="sidebar">
    <div class="user-card" id="profileBtn">
        <div class="user-avatar">{{ avatar }}</div>
        <div class="user-name">{{ username }}{% if role == 'owner' %}<span class="badge-owner">ВЛ</span>{% elif role == 'admin' %}<span class="badge-admin">АДМ</span>{% endif %}</div>
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
    <div class="section-title">⚙️ Настройки</div>
    <button id="themeToggleBtn" style="padding:10px; background:#e0e7ff; border:none; border-radius:20px; margin-bottom:8px; cursor:pointer;">🌙 Тёмная тема</button>
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
        <span class="close-btn" id="closeModal">&times;</span>
        <h3>👤 Личный профиль</h3>
        <label>Аватар (эмодзи или текст):</label>
        <input type="text" id="avatarInput" maxlength="2" placeholder="😀">
        <label>Новое имя (3-20 символов):</label>
        <input type="text" id="newNameInput" placeholder="Новое имя">
        <label>Новый пароль (мин. 4 символа):</label>
        <input type="password" id="newPasswordInput" placeholder="Новый пароль">
        <button id="saveProfileBtn">💾 Сохранить</button>
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
    
    // Тёмная тема
    function applyTheme() {
        if(darkMode) {
            document.body.classList.add('dark');
        } else {
            document.body.classList.remove('dark');
        }
    }
    applyTheme();
    
    document.getElementById('themeToggleBtn')?.addEventListener('click', () => {
        darkMode = !darkMode;
        applyTheme();
        fetch('/save_theme', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({theme: darkMode ? 'dark' : 'light'})
        });
    });
    
    // Профиль
    const modal = document.getElementById('profileModal');
    document.getElementById('profileBtn')?.addEventListener('click', () => modal.style.display = 'flex');
    document.getElementById('closeModal')?.addEventListener('click', () => modal.style.display = 'none');
    window.onclick = (e) => { if(e.target === modal) modal.style.display = 'none'; };
    
    document.getElementById('saveProfileBtn')?.addEventListener('click', () => {
        const newAvatar = document.getElementById('avatarInput').value;
        const newName = document.getElementById('newNameInput').value;
        const newPassword = document.getElementById('newPasswordInput').value;
        fetch('/update_profile', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({avatar: newAvatar, new_name: newName, new_password: newPassword})
        }).then(res => res.json()).then(data => {
            if(data.success) {
                alert('Профиль обновлён! Перезагрузите страницу для применения изменений.');
                modal.style.display = 'none';
                if(newName) setTimeout(() => location.reload(), 1000);
            } else alert('Ошибка: ' + data.error);
        });
    });
    
    function addMessage(name, text, time, isOwn, avatar) {
        let div = document.createElement('div');
        div.className = `message ${isOwn ? 'message-own' : ''}`;
        div.innerHTML = `
            <div class="message-avatar">${avatar || '👤'}</div>
            <div class="message-content">
                <div class="message-name">${escapeHtml(name)}<span class="message-time">${time}</span></div>
                <div class="message-text">${escapeHtml(text)}</div>
            </div>
        `;
        messagesDiv.appendChild(div);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    
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
        history.forEach(msg => addMessage(msg.name, msg.text, msg.time, msg.name === username, msg.avatar));
    });
    
    socket.on('new_message', (msg) => {
        addMessage(msg.name, msg.text, msg.time, msg.name === username, msg.avatar);
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
        container.innerHTML = usersList.map(u => `<div class="user-item">${u.avatar || '👤'} ${escapeHtml(u.name)} ${u.role === 'owner' ? '<span class="badge-owner">ВЛ</span>' : (u.role === 'admin' ? '<span class="badge-admin">АДМ</span>' : '')}</div>`).join('');
        onlineCountSpan.innerText = `👥 ${usersList.length}`;
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
            if(text.startsWith('/unadmin ')) {
                let target = text.split(' ')[1];
                fetch('/remove_admin', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username: target})})
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
    role_name = {'owner': 'Владелец', 'admin': 'Админ', 'moderator': 'Модератор', 'user': 'Пользователь'}.get(user['role'], 'Пользователь')
    user_theme = user.get('theme', 'light')
    return render_template_string(CHAT_HTML, username=session['username'], role=user['role'], role_name=role_name, avatar=user.get('avatar', '👤'), user_theme=user_theme)

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
        users[username] = {'password': hashlib.sha256(password.encode()).hexdigest(), 'role': 'user', 'avatar': '👤', 'banned': False, 'theme': 'light', 'created_at': datetime.now().isoformat()}
        save_users(users)
        return redirect(url_for('login'))
    return render_template_string(REGISTER_PAGE, error=None)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/save_theme', methods=['POST'])
def save_theme():
    if 'username' not in session:
        return {'error': 'Not logged in'}, 401
    data = request.json
    theme = data.get('theme', 'light')
    users[session['username']]['theme'] = theme
    save_users(users)
    return {'success': True}

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'username' not in session:
        return {'error': 'Not logged in'}, 401
    data = request.json
    username = session['username']
    avatar = data.get('avatar')
    new_name = data.get('new_name')
    new_password = data.get('new_password')
    if avatar and len(avatar) <= 2:
        users[username]['avatar'] = avatar
    if new_name:
        if len(new_name) < 3 or len(new_name) > 20:
            return {'error': 'Имя от 3 до 20 символов'}, 400
        if new_name in users and new_name != username:
            return {'error': 'Имя уже занято'}, 400
        users[new_name] = users.pop(username)
        session['username'] = new_name
        username = new_name
    if new_password and len(new_password) >= 4:
        users[username]['password'] = hashlib.sha256(new_password.encode()).hexdigest()
    save_users(users)
    return {'success': True, 'new_name': new_name if new_name else None}

@app.route('/remove_admin', methods=['POST'])
def remove_admin():
    if 'username' not in session or users[session['username']]['role'] != 'owner':
        return {'message': 'Только владелец может снимать админку'}
    target = request.json.get('username')
    if target in users and users[target]['role'] == 'admin':
        users[target]['role'] = 'user'
        save_users(users)
        return {'message': f'У {target} снята роль администратора'}
    return {'message': 'Пользователь не найден или не является админом'}

# ==================== SOCKETIO ====================
@socketio.on('join')
def handle_join(data):
    username = session.get('username')
    if not username or users.get(username, {}).get('banned'):
        return
    room = data['room']
    join_room(room)
    emit('history', messages.get(room, []), to=request.sid)

@socketio.on('send_message')
def handle_send_message(data):
    username = session.get('username')
    if not username or users.get(username, {}).get('banned'):
        return
    room = data['room']
    text = data['text']
    message = {'name': username, 'text': text, 'time': datetime.now().strftime('%H:%M:%S'), 'avatar': users[username].get('avatar', '👤')}
    if room not in messages:
        messages[room] = []
    messages[room].append(message)
    if len(messages[room]) > 100:
        messages[room] = messages[room][-100:]
    save_messages(messages)
    emit('new_message', message, to=room, broadcast=True)

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
        emit('rooms_update', rooms, broadcast=True)

@socketio.on('typing')
def handle_typing(data):
    username = session.get('username')
    if not username:
        return
    emit('typing_status', {'name': username, 'typing': data['typing']}, to=data['room'], broadcast=True, include_self=False)

@socketio.on('get_rooms')
def handle_get_rooms():
    emit('rooms_update', rooms)

@socketio.on('get_users')
def handle_get_users():
    users_list = [{'name': name, 'role': data['role'], 'avatar': data.get('avatar', '👤')} for name, data in users.items() if not data.get('banned')]
    emit('users_update', users_list, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
