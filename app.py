import os
import json
import hashlib
import random
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, session, redirect, url_for, jsonify, Response
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
app.secret_key = 'secret-key-2024'
socketio = SocketIO(app, cors_allowed_origins="*")

DB_PATH = 'db'
os.makedirs(DB_PATH, exist_ok=True)

USERS_FILE = os.path.join(DB_PATH, 'users.json')
MESSAGES_FILE = os.path.join(DB_PATH, 'messages.json')
ROOMS_FILE = os.path.join(DB_PATH, 'rooms.json')
FRIENDS_FILE = os.path.join(DB_PATH, 'friends.json')
DMS_FILE = os.path.join(DB_PATH, 'dms.json')

# -------------------------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ --------------------------
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {
        'MrAizex': {'password': hashlib.sha256('admin123'.encode()).hexdigest(), 'role': 'owner', 'avatar': '👑', 'avatar_base64': None, 'bio': 'Владелец', 'banned': False, 'muted_until': None, 'online': False, 'user_id': str(random.randint(1000, 99999999)), 'id_change_count': 0, 'last_id_change': None},
        'dimooon': {'password': hashlib.sha256('1111'.encode()).hexdigest(), 'role': 'admin', 'avatar': '😎', 'avatar_base64': None, 'bio': 'Админ', 'banned': False, 'muted_until': None, 'online': False, 'user_id': str(random.randint(1000, 99999999)), 'id_change_count': 0, 'last_id_change': None}
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
    return ['Главная']

def save_rooms(r):
    with open(ROOMS_FILE, 'w') as f:
        json.dump(r, f)

def load_friends():
    if os.path.exists(FRIENDS_FILE):
        with open(FRIENDS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_friends(f):
    with open(FRIENDS_FILE, 'w') as f:
        json.dump(f, f)

def load_dms():
    if os.path.exists(DMS_FILE):
        with open(DMS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_dms(d):
    with open(DMS_FILE, 'w') as f:
        json.dump(d, f)

users = load_users()
messages = load_messages()
rooms = load_rooms()
friends = load_friends()
dms = load_dms()

# -------------------------- HTML ШАБЛОНЫ --------------------------
LOGIN_HTML = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Чатик</title><style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}.card{background:rgba(255,255,255,0.95);border-radius:48px;padding:40px;max-width:400px;width:100%;text-align:center;box-shadow:0 25px 50px -12px rgba(0,0,0,0.25)}h1{margin-bottom:8px;background:linear-gradient(135deg,#667eea,#764ba2);-webkit-background-clip:text;-webkit-text-fill-color:transparent}.subtitle{color:#6b7280;margin-bottom:32px}input{width:100%;padding:16px;border:2px solid #e5e7eb;border-radius:32px;margin-bottom:16px;outline:none}input:focus{border-color:#667eea}button{width:100%;padding:16px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border:none;border-radius:32px;cursor:pointer}.error{background:#fee2e2;color:#dc2626;padding:12px;border-radius:24px;margin-bottom:20px}.footer{margin-top:24px}a{color:#667eea}
</style>
</head>
<body><div class="card"><h1>💬 Чатик</h1><div class="subtitle">Общайся с друзьями</div>{% if error %}<div class="error">{{ error }}</div>{% endif %}<form method="post"><input type="text" name="username" placeholder="Имя" required autofocus><input type="password" name="password" placeholder="Пароль" required><button type="submit">Войти</button></form><div class="footer">Нет аккаунта? <a href="/register">Регистрация</a></div></div></body>
</html>'''

REGISTER_HTML = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Регистрация</title><style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}.card{background:rgba(255,255,255,0.95);border-radius:48px;padding:40px;max-width:400px;width:100%;text-align:center;box-shadow:0 25px 50px -12px rgba(0,0,0,0.25)}h1{margin-bottom:32px;background:linear-gradient(135deg,#667eea,#764ba2);-webkit-background-clip:text;-webkit-text-fill-color:transparent}input{width:100%;padding:16px;border:2px solid #e5e7eb;border-radius:32px;margin-bottom:16px;outline:none}input:focus{border-color:#667eea}button{width:100%;padding:16px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border:none;border-radius:32px;cursor:pointer}.error{background:#fee2e2;color:#dc2626;padding:12px;border-radius:24px;margin-bottom:20px}.footer{margin-top:24px}a{color:#667eea}
</style>
</head>
<body><div class="card"><h1>📝 Регистрация</h1>{% if error %}<div class="error">{{ error }}</div>{% endif %}<form method="post"><input type="text" name="username" placeholder="Имя (3-20)" required autofocus><input type="password" name="password" placeholder="Пароль (мин 4)" required><button type="submit">Создать</button></form><div class="footer">Уже есть? <a href="/login">Войти</a></div></div></body>
</html>'''

CHAT_HTML = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes"><title>Чатик</title><script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script><style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:linear-gradient(135deg,#1e1b4b,#4c1d95);height:100vh;display:flex;overflow:hidden;transition:background 0.3s}body.dark{background:#0f0f0f}.sidebar{width:280px;background:rgba(255,255,255,0.95);backdrop-filter:blur(10px);border-right:1px solid rgba(0,0,0,0.1);display:flex;flex-direction:column;overflow-y:auto;transition:background 0.3s,color 0.3s}body.dark .sidebar{background:#1a1a1a;color:#fff;border-color:#333}.user-card{text-align:center;padding:24px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;cursor:pointer;margin-bottom:16px}body.dark .user-card{background:linear-gradient(135deg,#4f46e5,#6d28d9)}.user-avatar{width:64px;height:64px;border-radius:50%;margin:0 auto 10px;background:rgba(255,255,255,0.2);display:flex;align-items:center;justify-content:center;font-size:36px;overflow:hidden}.user-avatar img{width:100%;height:100%;object-fit:cover}.user-name{font-size:18px;font-weight:700}.user-bio{font-size:11px;opacity:0.85;margin-top:5px}.user-id{font-size:9px;opacity:0.6;margin-top:3px}.section-title{font-weight:600;padding:16px 20px 8px 20px;color:#475569;font-size:12px;text-transform:uppercase}body.dark .section-title{color:#94a3b8}.search-box{padding:8px 12px;margin:8px 12px;background:rgba(0,0,0,0.05);border-radius:40px;display:flex;align-items:center;gap:8px}body.dark .search-box{background:rgba(255,255,255,0.1)}.search-box input{background:none;border:none;outline:none;flex:1;color:inherit}.room-item,.user-item{padding:12px 20px;margin:4px 12px;border-radius:16px;cursor:pointer;display:flex;align-items:center;gap:12px;transition:0.2s}.room-item:hover,.user-item:hover{background:rgba(0,0,0,0.05)}body.dark .room-item:hover,body.dark .user-item:hover{background:rgba(255,255,255,0.1)}.room-item.active{background:#4f46e5;color:#fff}.room-menu{position:relative}.room-menu-btn{background:none;border:none;cursor:pointer;font-size:16px;margin-left:auto;padding:4px 8px;border-radius:20px}.room-menu-content{display:none;position:absolute;right:0;top:30px;background:#fff;border-radius:16px;box-shadow:0 5px 15px rgba(0,0,0,0.2);z-index:100;min-width:120px}body.dark .room-menu-content{background:#1a1a1a}.room-menu-content button{width:100%;padding:8px 16px;text-align:left;background:none;border:none;cursor:pointer}.room-menu-content button:hover{background:rgba(0,0,0,0.05)}.add-room{display:flex;gap:8px;margin:12px}.add-room input{flex:1;padding:10px;border-radius:40px;border:1px solid #ddd;outline:none}body.dark .add-room input{background:#333;color:#fff;border-color:#555}.add-room button{background:#4f46e5;color:#fff;border:none;border-radius:40px;padding:8px 20px;cursor:pointer}.chat-area{flex:1;display:flex;flex-direction:column;background:#fff;transition:background 0.3s}body.dark .chat-area{background:#0a0a0a}.chat-header{padding:16px 24px;background:#fff;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center}body.dark .chat-header{background:#1a1a1a;border-color:#333;color:#fff}.header-buttons{display:flex;gap:12px;align-items:center}.room-name-btn{background:none;border:none;font-weight:600;font-size:1rem;cursor:pointer;color:inherit}.dm-back-btn{background:none;border:none;cursor:pointer;font-size:1rem;color:inherit}.messages{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:8px;will-change:transform}.message{display:flex;gap:10px;align-items:flex-start;animation:fadeIn 0.2s ease-out}.message-own{justify-content:flex-end}.message-avatar{width:36px;height:36px;border-radius:50%;background:#4f46e5;display:flex;align-items:center;justify-content:center;font-size:16px;cursor:pointer;flex-shrink:0;overflow:hidden}.message-avatar img{width:100%;height:100%;object-fit:cover}.message-content{background:#f1f5f9;padding:8px 12px;border-radius:18px;max-width:65%;word-break:break-word;position:relative}body.dark .message-content{background:#2a2a2a;color:#e2e8f0}.message-own .message-content{background:#4f46e5;color:#fff}.message-name{font-weight:700;font-size:12px;display:flex;align-items:center;gap:6px;margin-bottom:2px}.message-time{font-size:9px;opacity:0.6;margin-left:6px}.message-text{margin-top:2px;font-size:14px;line-height:1.4}.message-actions{position:absolute;right:-28px;top:4px;display:flex;gap:4px;opacity:0;transition:opacity 0.2s}.message:hover .message-actions{opacity:1}.delete-msg{background:#374151;border:none;border-radius:50%;width:24px;height:24px;color:#fff;cursor:pointer;font-size:12px;display:flex;align-items:center;justify-content:center;transition:transform 0.1s}.delete-msg:active{transform:scale(0.9)}.badge-owner{background:#ef4444;font-size:8px;padding:2px 6px;border-radius:20px}.badge-admin{background:#10b981;font-size:8px;padding:2px 6px;border-radius:20px}.online-dot{width:8px;height:8px;background:#10b981;border-radius:50%;display:inline-block;margin-right:8px}.system-msg{text-align:center;font-size:11px;color:#64748b;padding:6px;margin:4px 0}.typing{padding:6px 24px;font-size:11px;color:#64748b;font-style:italic}.input-area{display:flex;gap:8px;padding:12px 20px;background:#fff;border-top:1px solid #eee;align-items:center}body.dark .input-area{background:#1a1a1a;border-color:#333}.input-area input{flex:1;padding:12px 16px;border:2px solid #e2e8f0;border-radius:40px;outline:none;font-size:14px}body.dark .input-area input{background:#2a2a2a;color:#fff;border-color:#444}.input-area button{background:#4f46e5;border:none;border-radius:50%;width:44px;height:44px;color:#fff;cursor:pointer;font-size:18px;display:flex;align-items:center;justify-content:center;transition:transform 0.1s}.input-area button:active{transform:scale(0.95)}.btn-settings,.btn-logout{margin:8px 12px;padding:12px;border-radius:20px;cursor:pointer;border:none;font-weight:500;transition:transform 0.1s}.btn-settings:active,.btn-logout:active{transform:scale(0.97)}.btn-settings{background:#e0e7ff;color:#4f46e5}body.dark .btn-settings{background:#2a2a2a;color:#818cf8}.btn-logout{background:#fee2e2;color:#dc2626}body.dark .btn-logout{background:#2a2a2a;color:#f87171}.modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);align-items:center;justify-content:center;z-index:2000}.modal-content{background:#fff;border-radius:28px;padding:24px;max-width:450px;width:90%;max-height:80vh;overflow-y:auto}body.dark .modal-content{background:#1a1a1a;color:#fff}.modal-content input,.modal-content textarea,.modal-content select{width:100%;padding:12px;margin:8px 0;border-radius:24px;border:1px solid #ddd;outline:none}body.dark .modal-content input,body.dark .modal-content textarea,body.dark .modal-content select{background:#2a2a2a;border-color:#444;color:#fff}.modal-content button{background:#4f46e5;color:#fff;border:none;padding:12px;border-radius:24px;width:100%;cursor:pointer;margin-top:8px;transition:transform 0.1s}.modal-content button:active{transform:scale(0.98)}.close{float:right;font-size:24px;cursor:pointer}.emoji-picker{position:absolute;bottom:80px;left:20px;background:#fff;border-radius:20px;padding:12px;display:none;grid-template-columns:repeat(6,1fr);gap:8px;box-shadow:0 10px 25px rgba(0,0,0,0.15);z-index:1000}body.dark .emoji-picker{background:#1a1a1a}.emoji{font-size:28px;cursor:pointer;text-align:center;padding:6px;border-radius:12px}.notify-btn{position:relative;background:none;border:none;cursor:pointer;font-size:20px;padding:8px;border-radius:50%}.notify-badge{position:absolute;top:-2px;right:-2px;background:#ef4444;color:#fff;font-size:10px;min-width:18px;height:18px;border-radius:20px;display:none;align-items:center;justify-content:center}.friend-request-item{display:flex;justify-content:space-between;align-items:center;padding:12px;margin:8px 0;background:#f1f5f9;border-radius:20px}body.dark .friend-request-item{background:#2a2a2a}.profile-avatar{width:100px;height:100px;border-radius:50%;margin:0 auto 12px;background:#e2e8f0;display:flex;align-items:center;justify-content:center;font-size:48px;overflow:hidden}.profile-avatar img{width:100%;height:100%;object-fit:cover}.profile-name{font-size:20px;font-weight:700;text-align:center;margin-bottom:4px}.profile-role{text-align:center;font-size:12px;color:#6b7280;margin-bottom:8px}.profile-id{text-align:center;font-size:11px;color:#94a3b8;margin-bottom:16px;font-family:monospace;cursor:pointer}.profile-bio{background:#f1f5f9;padding:12px;border-radius:20px;margin:16px 0;font-size:14px}body.dark .profile-bio{background:#2a2a2a}.profile-actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:16px}.profile-actions button{flex:1;padding:10px;border-radius:24px;border:none;cursor:pointer;font-weight:500;transition:transform 0.1s}.profile-actions button:active{transform:scale(0.97)}.toast{position:fixed;bottom:20px;right:20px;background:#4f46e5;color:#fff;padding:12px 20px;border-radius:40px;z-index:3000;animation:slideIn 0.3s;box-shadow:0 5px 15px rgba(0,0,0,0.2)}@keyframes slideIn{from{transform:translateX(100%);opacity:0}to{transform:translateX(0);opacity:1}}.file-message{background:rgba(79,70,229,0.1);padding:6px 10px;border-radius:16px;display:inline-flex;align-items:center;gap:8px}.file-message a{color:#4f46e5;text-decoration:none}.image-preview{max-width:180px;max-height:180px;border-radius:12px;cursor:pointer;margin-top:4px}.fullscreen-image{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.9);display:flex;align-items:center;justify-content:center;z-index:5000;cursor:pointer}.fullscreen-image img{max-width:90%;max-height:90%;object-fit:contain}.dm-send-btn{background:#4f46e5;border:none;border-radius:20px;padding:10px 20px;color:#fff;cursor:pointer}.confirm-dialog{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#fff;border-radius:28px;padding:24px;z-index:4000;box-shadow:0 10px 25px rgba(0,0,0,0.2);min-width:280px;text-align:center}body.dark .confirm-dialog{background:#1a1a1a;color:#fff}.confirm-dialog-buttons{display:flex;gap:12px;justify-content:center;margin-top:20px}.confirm-dialog-buttons button{padding:8px 20px;border-radius:20px;border:none;cursor:pointer}@media(max-width:680px){.sidebar{width:240px}.message-content{max-width:75%}}
</style>
</head>
<body>
<div class="sidebar">
    <div class="user-card" id="profileBtn">
        <div class="user-avatar">{% if avatar_base64 %}<img src="{{ avatar_base64 }}">{% else %}{{ avatar }}{% endif %}</div>
        <div class="user-name">{{ username }}{% if role == "owner" %}<span class="badge-owner"> ВЛ</span>{% elif role == "admin" %}<span class="badge-admin"> АДМ</span>{% endif %}</div>
        <div class="user-bio">{{ bio[:40] }}</div>
        <div class="user-id">ID: {{ user_id }}</div>
    </div>
    <div class="search-box"><input type="text" id="searchUsers" placeholder="🔍 Поиск..."></div>
    <div class="section-title">🏠 КОМНАТЫ</div>
    <div id="roomsList"></div>
    {% if role in ["owner", "admin"] %}
    <div class="add-room"><input type="text" id="newRoom" placeholder="Название"><button id="createRoomBtn">+</button></div>
    {% endif %}
    <div class="section-title">👥 ОНЛАЙН</div>
    <div id="usersList"></div>
    <div class="section-title">👫 ДРУЗЬЯ</div>
    <div id="friendsList"></div>
    <div class="section-title">💬 ЛИЧНЫЕ СООБЩЕНИЯ</div>
    <div id="dmList" class="dm-list"></div>
    <button class="btn-settings" id="settingsBtn">⚙️ Настройки</button>
    <button class="btn-logout" id="logoutBtn">🚪 Выйти</button>
</div>
<div class="chat-area">
    <div class="chat-header">
        <div class="header-buttons">
            <button class="room-name-btn" id="roomNameBtn"><span id="roomName">Главная</span></button>
            <button class="dm-back-btn" id="dmBackBtn" style="display:none;">← Назад</button>
        </div>
        <button class="notify-btn" id="notifyBtn"><span class="notify-badge" id="notifyBadge">0</span>🔔</button>
    </div>
    <div id="messagesList" class="messages"></div>
    <div id="typingStatus" class="typing"></div>
    <div class="input-area" id="inputArea">
        <button id="emojiBtn">😊</button>
        <button id="fileBtn">📎</button>
        <input type="text" id="messageInput" placeholder="Сообщение...">
        <button id="sendBtn">📤</button>
        <input type="file" id="fileInput" style="display:none" accept="image/*,application/pdf,text/plain">
        <input type="file" id="avatarFileInput" style="display:none" accept="image/jpeg,image/png">
    </div>
</div>

<div id="emojiPicker" class="emoji-picker"></div>
<div id="profileModal" class="modal"><div class="modal-content"><span class="close" id="closeProfile">&times;</span><h3>👤 Мой профиль</h3><label>Аватар (эмодзи):</label><input type="text" id="avatarInput" maxlength="2" placeholder="😀"><label>Загрузить изображение:</label><button id="uploadAvatarBtn" style="background:#4f46e5;color:#fff">📷 Выбрать фото</button><label>О себе:</label><textarea id="bioInput" rows="3">{{ bio }}</textarea><label>Новое имя:</label><input type="text" id="newName"><label>Новый пароль:</label><input type="password" id="newPass"><div id="idChangeInfo"></div><button id="changeIdBtn">🆔 Сменить ID</button><button id="saveProfile">💾 Сохранить</button></div></div>
<div id="settingsModal" class="modal"><div class="modal-content"><span class="close" id="closeSettings">&times;</span><h3>⚙️ Настройки</h3><button id="themeBtn">🌙 Тёмная тема</button><button id="clearHistoryBtn">🗑️ Очистить историю чата</button><button id="exportChatBtn">📁 Экспорт чата</button><button id="changePasswordBtn">🔑 Сменить пароль</button></div></div>
<div id="notifyModal" class="modal"><div class="modal-content"><span class="close" id="closeNotifyModal">&times;</span><h3>🔔 Уведомления</h3><div id="notificationsList"></div></div></div>
<div id="userModal" class="modal"><div class="modal-content"><span class="close" id="closeUserModal">&times;</span><div id="userModalContent"></div></div></div>

<script>
let socket=io(),currentRoom='Главная',username='{{ username }}',role='{{ role }}',user_id='{{ user_id }}',typingUsers={};
let notifications=[],pendingFriendRequests=[],currentDMTarget=null,isDMmode=false;
const msgDiv=document.getElementById('messagesList'),msgInput=document.getElementById('messageInput');

function showToast(msg,type='success'){
    let t=document.createElement('div');t.className='toast';t.style.background=type==='success'?'#10b981':(type==='error'?'#ef4444':'#4f46e5');t.innerHTML=msg;document.body.appendChild(t);setTimeout(()=>t.remove(),3000);
}
function confirmDialog(msg,onYes){
    let div=document.createElement('div');div.className='confirm-dialog';div.innerHTML=`<p>${msg}</p><div class="confirm-dialog-buttons"><button id="confirmYes">Да</button><button id="confirmNo">Нет</button></div>`;
    document.body.appendChild(div);
    document.getElementById('confirmYes').onclick=()=>{onYes();div.remove();};
    document.getElementById('confirmNo').onclick=()=>div.remove();
}
const savedTheme = localStorage.getItem('chatTheme');
if(savedTheme === 'dark'){document.body.classList.add('dark');}
document.getElementById('themeBtn').onclick=()=>{
    document.body.classList.toggle('dark');
    localStorage.setItem('chatTheme',document.body.classList.contains('dark')?'dark':'light');
};
document.getElementById('roomNameBtn').onclick=()=>{
    if(isDMmode){
        isDMmode=false; currentDMTarget=null;
        document.getElementById('roomNameBtn').style.display='inline-block';
        document.getElementById('dmBackBtn').style.display='none';
        document.getElementById('roomName').innerText=currentRoom;
        socket.emit('join',{room:currentRoom});
    }else if(currentRoom!=='Главная'){
        socket.emit('switch',{old:currentRoom,new:'Главная'});
        currentRoom='Главная';
        document.getElementById('roomName').innerText='Главная';
        document.querySelectorAll('.room-item').forEach(i=>i.classList.remove('active'));
        let mainRoom=Array.from(document.querySelectorAll('.room-item')).find(el=>el.dataset.room==='Главная');
        if(mainRoom)mainRoom.classList.add('active');
        msgDiv.innerHTML='<div class="system-msg">⏳ Загрузка...</div>';
    }
};
document.getElementById('dmBackBtn').onclick=()=>{
    isDMmode=false; currentDMTarget=null;
    document.getElementById('roomNameBtn').style.display='inline-block';
    document.getElementById('dmBackBtn').style.display='none';
    document.getElementById('roomName').innerText=currentRoom;
    socket.emit('join',{room:currentRoom});
};
function addNotification(title,text){notifications.unshift({title,text,time:new Date().toLocaleTimeString()});if(notifications.length>20)notifications.pop();updateBadge();updateNotifList();}
function updateBadge(){let b=document.getElementById('notifyBadge');let c=notifications.length+pendingFriendRequests.length;if(c>0){b.textContent=c>99?'99+':c;b.style.display='flex';}else b.style.display='none';}
function updateNotifList(){
    let c=document.getElementById('notificationsList');
    if(notifications.length===0&&pendingFriendRequests.length===0){c.innerHTML='<p style="color:#6b7280;text-align:center;padding:16px">Нет уведомлений</p>';return;}
    let h='';
    pendingFriendRequests.forEach(r=>{h+=`<div class="friend-request-item"><span>📨 Заявка от ${escape(r)}</span><button onclick="acceptReq('${escape(r)}')" style="background:#10b981;border:none;border-radius:20px;padding:6px 14px;color:#fff;cursor:pointer">Принять</button></div>`;});
    notifications.forEach(n=>{h+=`<div class="friend-request-item"><div><strong>${escape(n.title)}</strong><br><small>${escape(n.text)}</small><br><span style="font-size:10px">${n.time}</span></div></div>`;});
    c.innerHTML=h;
}
function loadRequests(){fetch('/get_friend_requests').then(r=>r.json()).then(data=>{pendingFriendRequests=data.requests||[];updateBadge();updateNotifList();});}
document.getElementById('notifyBtn').onclick=()=>{document.getElementById('notifyModal').style.display='flex';updateNotifList();};
document.getElementById('closeNotifyModal').onclick=()=>document.getElementById('notifyModal').style.display='none';
fetch('/id_change_info').then(r=>r.json()).then(data=>{let d=document.getElementById('idChangeInfo');if(data.can_change)d.innerHTML='<p style="color:#10b981;margin:8px 0">✅ Можно сменить ID</p>';else d.innerHTML=`<p style="color:#f59e0b;margin:8px 0">⚠️ Следующая смена ID ${data.next_change_date}</p>`;});
document.getElementById('changeIdBtn').onclick=()=>{
    let nid=prompt('Новый ID (4-8 цифр):');
    if(nid&&/^\\d{4,8}$/.test(nid)){
        fetch('/change_id',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({new_id:nid})}).then(r=>r.json()).then(data=>{
            if(data.success){showToast('✅ ID изменён!','success');setTimeout(()=>location.reload(),1500);}
            else showToast('❌ '+data.error,'error');
        });
    }else showToast('❌ ID должен содержать 4-8 цифр','error');
};
let tempAvatarBase64=null;
document.getElementById('uploadAvatarBtn').onclick=()=>document.getElementById('avatarFileInput').click();
document.getElementById('avatarFileInput').onchange=function(e){
    let file=e.target.files[0];
    if(file&&file.type.startsWith('image/')){
        let reader=new FileReader();
        reader.onload=function(ev){tempAvatarBase64=ev.target.result;showToast('✅ Изображение выбрано, сохраните профиль','success');};
        reader.readAsDataURL(file);
    }else{showToast('❌ Выберите изображение','error');}
    e.target.value='';
};
document.getElementById('fileBtn').onclick=()=>document.getElementById('fileInput').click();
document.getElementById('fileInput').onchange=function(e){
    let file=e.target.files[0];
    if(!file)return;
    let reader=new FileReader();
    reader.onload=function(ev){
        let data=ev.target.result;
        let isImage=file.type.startsWith('image/');
        socket.emit('file_message',{name:file.name,data:data,type:file.type,isImage:isImage,room:currentRoom});
    };
    reader.readAsDataURL(file);
    e.target.value='';
};
function loadDMList(){fetch('/get_dm_list').then(r=>r.json()).then(data=>{let c=document.getElementById('dmList');if(data.dms&&data.dms.length){c.innerHTML=data.dms.map(d=>`<div class="user-item" onclick="openDM('${escape(d.with)}')"><span>💬 ${escape(d.with)}</span><span style="font-size:10px;color:#94a3b8">${escape(d.last_preview)}</span></div>`).join('');}else c.innerHTML='<div class="user-item" style="color:#94a3b8">Нет диалогов</div>';});}
function openDM(t){
    isDMmode=true; currentDMTarget=t;
    document.getElementById('roomNameBtn').style.display='none';
    document.getElementById('dmBackBtn').style.display='inline-block';
    document.getElementById('roomName').innerText=t;
    fetch('/get_dm/'+encodeURIComponent(t)).then(r=>r.json()).then(data=>{
        msgDiv.innerHTML='';
        data.messages.forEach(m=>{
            let timeStr=m.time;
            if(m.timestamp) timeStr=new Date(m.timestamp).toLocaleString();
            let div=document.createElement('div');div.className=`message ${m.from===username?'message-own':''}`;
            let badge='';if(m.from==='MrAizex')badge='<span class="badge-owner">ВЛ</span>';else if(m.from==='dimooon')badge='<span class="badge-admin">АДМ</span>';
            fetch('/user_avatar/'+encodeURIComponent(m.from)).then(r=>r.json()).then(avatar=>{
                let avatarHtml=avatar.avatar_base64?`<img src="${avatar.avatar_base64}">`:'👤';
                div.innerHTML=`
                    <div class="message-avatar" onclick="showUserProfile('${escape(m.from)}')">${avatarHtml}</div>
                    <div class="message-content"><div class="message-name">${escape(m.from)}${badge}<span class="message-time">${timeStr}</span></div><div class="message-text">${escape(m.text)}</div></div>
                `;
                msgDiv.appendChild(div);msgDiv.scrollTop=msgDiv.scrollHeight;
            });
        });
    });
}
document.getElementById('dmSendBtn')?.addEventListener('click',function(){
    let txt=document.getElementById('dmInput').value.trim();
    if(txt&&currentDMTarget){
        socket.emit('private_message',{target:currentDMTarget,text:txt});
        document.getElementById('dmInput').value='';
        let timeStr=new Date().toLocaleString();
        let div=document.createElement('div');div.className='message message-own';
        div.innerHTML=`
            <div class="message-avatar">{% if avatar_base64 %}<img src="{{ avatar_base64 }}">{% else %}{{ avatar }}{% endif %}</div>
            <div class="message-content"><div class="message-name">{{ username }}<span class="message-time">${timeStr}</span></div><div class="message-text">${escape(txt)}</div></div>
        `;
        msgDiv.appendChild(div);msgDiv.scrollTop=msgDiv.scrollHeight;
    }
});
socket.on('private_message',(data)=>{
    if(isDMmode && (data.from===currentDMTarget || data.to===currentDMTarget)){
        let timeStr=data.time;
        if(data.timestamp) timeStr=new Date(data.timestamp).toLocaleString();
        let div=document.createElement('div');div.className=`message ${data.from===username?'message-own':''}`;
        let badge='';if(data.from==='MrAizex')badge='<span class="badge-owner">ВЛ</span>';else if(data.from==='dimooon')badge='<span class="badge-admin">АДМ</span>';
        fetch('/user_avatar/'+encodeURIComponent(data.from)).then(r=>r.json()).then(avatar=>{
            let avatarHtml=avatar.avatar_base64?`<img src="${avatar.avatar_base64}">`:'👤';
            div.innerHTML=`
                <div class="message-avatar" onclick="showUserProfile('${escape(data.from)}')">${avatarHtml}</div>
                <div class="message-content"><div class="message-name">${escape(data.from)}${badge}<span class="message-time">${timeStr}</span></div><div class="message-text">${escape(data.text)}</div></div>
            `;
            msgDiv.appendChild(div);msgDiv.scrollTop=msgDiv.scrollHeight;
        });
    }
    if(!isDMmode)addNotification('Личное сообщение',`${data.from}: ${data.text.substring(0,30)}`);
    loadDMList();
});
const emojis=['😀','😂','❤️','👍','🎉','🔥','😍','🥹','😭','🤔','👋','🙏','✨','💯','😎','🥳'];
const picker=document.getElementById('emojiPicker');picker.innerHTML=emojis.map(e=>`<div class="emoji">${e}</div>`).join('');
document.querySelectorAll('.emoji').forEach(el=>el.onclick=()=>{msgInput.value+=el.textContent;msgInput.focus();picker.style.display='none';});
document.getElementById('emojiBtn').onclick=(e)=>{e.stopPropagation();picker.style.display=picker.style.display==='grid'?'none':'grid';};
document.addEventListener('click',(e)=>{if(!e.target.closest('#emojiBtn')&&!e.target.closest('.emoji-picker'))picker.style.display='none';});
function showUserProfile(name){
    fetch('/user_info/'+encodeURIComponent(name)).then(r=>r.json()).then(data=>{
        let actions='';
        if(!data.is_friend&&name!==username)actions+=`<button onclick="addFriend('${name}')" style="background:#10b981;color:#fff">➕ В друзья</button>`;
        if(data.is_friend)actions+=`<button onclick="removeFriend('${name}')" style="background:#ef4444;color:#fff">❌ Удалить</button>`;
        actions+=`<button onclick="openDM('${name}')" style="background:#8b5cf6;color:#fff">💬 Личка</button>`;
        if(role==='owner'||role==='admin'){
            if(data.user_role==='admin')actions+=`<button onclick="unadminUser('${name}')" style="background:#f59e0b;color:#fff">🔻 Снять админку</button>`;
            else if(data.user_role!=='owner')actions+=`<button onclick="giveAdmin('${name}')" style="background:#10b981;color:#fff">⭐ Выдать админку</button>`;
        }
        if(role==='owner'||role==='admin'){
            if(data.muted)actions+=`<button onclick="unmuteUser('${name}')" style="background:#10b981;color:#fff">🔊 Размутить</button>`;
            else actions+=`<select id="muteTime" style="width:100%;padding:8px;border-radius:20px;margin-bottom:8px"><option value="5">5 мин</option><option value="30">30 мин</option><option value="60">1 час</option><option value="1440">1 день</option><option value="10080">1 нед</option></select><button onclick="muteUser('${name}')" style="background:#f59e0b;color:#fff">🔇 Замутить</button>`;
            if(data.banned)actions+=`<button onclick="unbanUser('${name}')" style="background:#10b981;color:#fff">🔓 Разбанить</button>`;
            else actions+=`<button onclick="banUser('${name}')" style="background:#ef4444;color:#fff">🔨 Забанить</button>`;
        }
        let avatarHtml='';
        if(data.avatar_base64)avatarHtml=`<img src="${data.avatar_base64}">`;
        else avatarHtml=data.avatar||'👤';
        document.getElementById('userModalContent').innerHTML=`
            <div class="profile-avatar">${avatarHtml}</div>
            <div class="profile-name">${escape(data.username)}</div>
            <div class="profile-role">${data.role_display}</div>
            <div class="profile-id" onclick="copyId('${data.user_id}')">🆔 ID: ${escape(data.user_id)} (скопировать)</div>
            <div class="profile-bio">📝 ${escape(data.bio||'Нет описания')}</div>
            <div class="profile-actions">${actions}</div>
        `;
        document.getElementById('userModal').style.display='flex';
    });
}
window.copyId=id=>{navigator.clipboard.writeText(id);showToast('✅ ID скопирован','success');};
window.muteUser=name=>{let t=document.getElementById('muteTime').value;fetch('/mute_user',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:name,minutes:t})}).then(r=>r.json()).then(data=>{addSystem(data.message);showToast(data.message,'warning');document.getElementById('userModal').style.display='none';});};
window.unmuteUser=name=>{fetch('/unmute_user',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);showToast(data.message,'success');document.getElementById('userModal').style.display='none';});};
window.banUser=name=>{fetch('/ban_user',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);showToast(data.message,'error');document.getElementById('userModal').style.display='none';});};
window.unbanUser=name=>{fetch('/unban_user',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);showToast(data.message,'success');document.getElementById('userModal').style.display='none';});};
window.addFriend=name=>{fetch('/add_friend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({friend:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);showToast(data.message,'success');addNotification('Заявка отправлена',name);document.getElementById('userModal').style.display='none';loadRequests();});};
window.removeFriend=name=>{fetch('/remove_friend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({friend:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);showToast(data.message,'info');addNotification('Друг удалён',name);document.getElementById('userModal').style.display='none';});};
window.giveAdmin=name=>{fetch('/give_admin',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);showToast(data.message,'success');addNotification('Админ',`${name} назначен`);document.getElementById('userModal').style.display='none';});};
window.unadminUser=name=>{fetch('/remove_admin',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);showToast(data.message,'warning');addNotification('Админ',`У ${name} снято`);document.getElementById('userModal').style.display='none';});};
window.acceptReq=name=>{fetch('/accept_friend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({friend:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);showToast(data.message,'success');addNotification('Новый друг',name);pendingFriendRequests=pendingFriendRequests.filter(r=>r!==name);updateBadge();updateNotifList();loadRequests();});};
function deleteRoom(roomName){
    confirmDialog(`Удалить комнату "${roomName}"?`,()=>{
        fetch('/delete_room',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({room:roomName})}).then(r=>r.json()).then(data=>{
            addSystem(data.message);
            if(data.success && currentRoom===roomName){
                if(!isDMmode)socket.emit('switch',{old:currentRoom,new:'Главная'});
                currentRoom='Главная';
                document.getElementById('roomName').innerText='Главная';
            }
            showToast(data.message,data.success?'success':'error');
        });
    });
}
function addSystem(t){let d=document.createElement('div');d.className='system-msg';d.textContent=t;msgDiv.appendChild(d);msgDiv.scrollTop=msgDiv.scrollHeight;}
function formatLocalTime(timestamp){
    let d=new Date(parseInt(timestamp));
    if(isNaN(d.getTime())) return timestamp;
    return d.toLocaleString();
}
function addMessage(id,name,text,time,isOwn,avatar,avatarBase64,isFile,fileData,fileName,isImage){
    let div=document.createElement('div');div.className=`message ${isOwn?'message-own':''}`;div.dataset.id=id;
    let badge='';if(name==='MrAizex')badge='<span class="badge-owner">ВЛ</span>';else if(name==='dimooon')badge='<span class="badge-admin">АДМ</span>';
    let avatarHtml='';
    if(avatarBase64)avatarHtml=`<img src="${avatarBase64}">`;
    else avatarHtml=avatar||'👤';
    let content='';
    if(isFile){
        if(isImage){
            content=`<div><img src="${fileData}" class="image-preview" onclick="showFullscreenImage('${fileData}')"></div>`;
        }else{
            content=`<div class="file-message"><span>📄</span><a href="${fileData}" download="${escape(fileName)}">${escape(fileName)}</a></div>`;
        }
    }else{
        content=escape(text);
    }
    div.innerHTML=`
        <div class="message-avatar" onclick="showUserProfile('${escape(name)}')">${avatarHtml}</div>
        <div class="message-content">
            <div class="message-name">${escape(name)}${badge}<span class="message-time">${time}</span></div>
            <div class="message-text">${content}</div>
            <div class="message-actions">
                ${(isOwn || role==='owner' || role==='admin') ? `<button class="delete-msg" onclick="deleteMessage('${id}')"><i class="fas fa-trash"></i></button>` : ''}
            </div>
        </div>
    `;
    msgDiv.appendChild(div);msgDiv.scrollTop=msgDiv.scrollHeight;
}
function showFullscreenImage(src){
    let overlay=document.createElement('div');overlay.className='fullscreen-image';
    let img=document.createElement('img');img.src=src;
    overlay.appendChild(img);
    overlay.onclick=()=>overlay.remove();
    document.body.appendChild(overlay);
}
function deleteMessage(msgId){
    confirmDialog('Удалить сообщение?',()=>{
        socket.emit('delete_message',{messageId:msgId,room:currentRoom});
    });
}
function escape(s){return s.replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'})[m]);}
socket.emit('join',{room:currentRoom});
socket.on('history',h=>{msgDiv.innerHTML='';h.forEach(m=>{
    let localTime=formatLocalTime(m.id);
    if(m.file)addMessage(m.id,m.name,'',localTime,m.name===username,m.avatar,m.avatar_base64,true,m.file.data,m.file.name,m.file.isImage);
    else addMessage(m.id,m.name,m.text,localTime,m.name===username,m.avatar,m.avatar_base64);
});});
socket.on('message',m=>{
    let localTime=formatLocalTime(m.id);
    if(m.file)addMessage(m.id,m.name,'',localTime,m.name===username,m.avatar,m.avatar_base64,true,m.file.data,m.file.name,m.file.isImage);
    else addMessage(m.id,m.name,m.text,localTime,m.name===username,m.avatar,m.avatar_base64);
});
socket.on('delete_message',data=>{
    document.querySelectorAll(`.message[data-id="${data.messageId}"]`).forEach(el=>el.remove());
    showToast('🗑️ Сообщение удалено','info');
});
socket.on('system',d=>addSystem(d.text));
socket.on('friend_request',data=>{addNotification('Заявка',`${data.from} хочет добавить вас`);loadRequests();});
socket.on('rooms',l=>{let c=document.getElementById('roomsList');c.innerHTML=l.map(r=>`<div class="room-item ${r===currentRoom?'active':''}" data-room="${r}">🏠 ${escape(r)}${role==='owner'||role==='admin'?`<div class="room-menu"><button class="room-menu-btn">⋯</button><div class="room-menu-content"><button onclick="event.stopPropagation();deleteRoom('${escape(r)}')">Удалить</button></div></div>`:''}</div>`).join('');document.querySelectorAll('.room-menu-btn').forEach(btn=>{btn.onclick=(e)=>{e.stopPropagation();let menu=btn.nextElementSibling;menu.style.display=menu.style.display==='block'?'none':'block';};});document.querySelectorAll('.room-item').forEach(el=>{el.onclick=()=>{let nr=el.dataset.room;if(nr===currentRoom||isDMmode)return;socket.emit('switch',{old:currentRoom,new:nr});currentRoom=nr;document.getElementById('roomName').innerText=currentRoom;document.querySelectorAll('.room-item').forEach(i=>i.classList.remove('active'));el.classList.add('active');msgDiv.innerHTML='<div class="system-msg">⏳ Загрузка...</div>';};});});
socket.on('users',l=>{
    let c=document.getElementById('usersList');
    let searchVal=document.getElementById('searchUsers').value.toLowerCase();
    let filtered=l.filter(u=>u.name.toLowerCase().includes(searchVal));
    c.innerHTML=filtered.map(u=>`<div class="user-item" onclick="showUserProfile('${escape(u.name)}')"><span class="online-dot"></span> ${u.avatar_base64?`<img src="${u.avatar_base64}" style="width:24px;height:24px;border-radius:50%;">`:u.avatar||'👤'} ${escape(u.name)} ${u.role==='owner'?'<span class="badge-owner">ВЛ</span>':(u.role==='admin'?'<span class="badge-admin">АДМ</span>':'')}<button onclick="event.stopPropagation();openDM('${escape(u.name)}')" style="background:none;border:none;cursor:pointer;margin-left:auto;font-size:16px">💬</button></div>`).join('');
    loadDMList();
});
document.getElementById('searchUsers').addEventListener('input',()=>{socket.emit('get_users');});
socket.on('friends',l=>{let c=document.getElementById('friendsList');if(c)c.innerHTML=l.map(f=>`<div class="user-item" onclick="showUserProfile('${escape(f.name)}')">👫 ${escape(f.name)}</div>`).join('');});
socket.on('typing',d=>{if(d.typing)typingUsers[d.name]=true;else delete typingUsers[d.name];let n=Object.keys(typingUsers).filter(n=>n!==username);document.getElementById('typingStatus').innerText=n.length?(n.length===1?`${n[0]} печатает...`:`${n.length} человек печатают...`):'';});
document.getElementById('sendBtn').onclick=()=>{let t=msgInput.value.trim();if(t){socket.emit('message',{text:t,room:currentRoom});msgInput.value='';}};
msgInput.onkeypress=e=>{if(e.key==='Enter')document.getElementById('sendBtn').click();socket.emit('typing',{room:currentRoom,typing:true});clearTimeout(window.tt);window.tt=setTimeout(()=>socket.emit('typing',{room:currentRoom,typing:false}),1000);};
document.getElementById('createRoomBtn')?.addEventListener('click',()=>{let n=document.getElementById('newRoom').value.trim();if(n){socket.emit('create',{room:n});document.getElementById('newRoom').value='';}});
document.getElementById('profileBtn').onclick=()=>document.getElementById('profileModal').style.display='flex';
document.getElementById('settingsBtn').onclick=()=>document.getElementById('settingsModal').style.display='flex';
document.getElementById('closeProfile').onclick=()=>document.getElementById('profileModal').style.display='none';
document.getElementById('closeSettings').onclick=()=>document.getElementById('settingsModal').style.display='none';
document.getElementById('closeUserModal').onclick=()=>document.getElementById('userModal').style.display='none';
document.getElementById('saveProfile').onclick=()=>{
    fetch('/update_profile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
        avatar:document.getElementById('avatarInput').value,
        avatar_base64:tempAvatarBase64,
        bio:document.getElementById('bioInput').value,
        new_name:document.getElementById('newName').value,
        new_password:document.getElementById('newPass').value
    })}).then(r=>r.json()).then(data=>{
        if(data.success){showToast('✅ Профиль сохранён','success');setTimeout(()=>location.reload(),1000);}
        else showToast('❌ '+data.error,'error');
    });
};
document.getElementById('logoutBtn').onclick=()=>window.location.href='/logout';
document.getElementById('clearHistoryBtn').onclick=()=>{
    confirmDialog('Очистить всю историю сообщений?',()=>{
        fetch('/clear_history',{method:'POST'}).then(r=>r.json()).then(data=>{
            if(data.success){showToast('История очищена','success');location.reload();}
            else showToast('Ошибка','error');
        });
    });
};
document.getElementById('exportChatBtn').onclick=()=>{
    fetch('/export_chat').then(r=>r.blob()).then(blob=>{
        let url=URL.createObjectURL(blob);
        let a=document.createElement('a');a.href=url;a.download='chat_history.json';a.click();
    });
};
document.getElementById('changePasswordBtn').onclick=()=>{
    let newPass=prompt('Введите новый пароль (мин 4)');
    if(newPass&&newPass.length>=4){
        fetch('/change_password',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({new_password:newPass})}).then(r=>r.json()).then(data=>{
            if(data.success)showToast('Пароль изменён','success');else showToast(data.error,'error');
        });
    }else showToast('Пароль не менее 4 символов','error');
};
window.onclick=e=>{
    if(e.target===document.getElementById('profileModal'))document.getElementById('profileModal').style.display='none';
    if(e.target===document.getElementById('settingsModal'))document.getElementById('settingsModal').style.display='none';
    if(e.target===document.getElementById('notifyModal'))document.getElementById('notifyModal').style.display='none';
    if(e.target===document.getElementById('userModal'))document.getElementById('userModal').style.display='none';
};
loadRequests();socket.emit('get_rooms');socket.emit('get_users');
</script>
</body>
</html>
'''

# -------------------------- МАРШРУТЫ --------------------------
@app.route('/')
def index():
    if 'username' not in session: return redirect(url_for('login'))
    u = users.get(session['username'])
    if not u or u.get('banned'): session.clear(); return redirect(url_for('login'))
    return render_template_string(CHAT_HTML, username=session['username'], role=u['role'], avatar=u.get('avatar','👤'), avatar_base64=u.get('avatar_base64'), bio=u.get('bio',''), user_id=u.get('user_id',''))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        name = request.form['username']; pwd = request.form['password']; h = hashlib.sha256(pwd.encode()).hexdigest()
        if name in users and users[name]['password'] == h:
            if users[name].get('banned'): return render_template_string(LOGIN_HTML, error='Заблокирован')
            session['username'] = name; return redirect(url_for('index'))
        return render_template_string(LOGIN_HTML, error='Неверные данные')
    return render_template_string(LOGIN_HTML)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['username']; pwd = request.form['password']
        if name in users: return render_template_string(REGISTER_HTML, error='Имя занято')
        if len(name) < 3 or len(name) > 20: return render_template_string(REGISTER_HTML, error='Имя 3-20')
        if len(pwd) < 4: return render_template_string(REGISTER_HTML, error='Пароль мин 4')
        users[name] = {'password': hashlib.sha256(pwd.encode()).hexdigest(), 'role': 'user', 'avatar': '👤', 'avatar_base64': None, 'bio': '', 'banned': False, 'muted_until': None, 'online': False, 'user_id': str(random.randint(1000, 99999999)), 'id_change_count': 0, 'last_id_change': None}
        save_users(users); return redirect(url_for('login'))
    return render_template_string(REGISTER_HTML)

@app.route('/logout')
def logout():
    if 'username' in session:
        users[session['username']]['online'] = False
        save_users(users)
        socketio.emit('user_offline', {'name': session['username']}, broadcast=True)
    session.clear(); return redirect(url_for('login'))

@app.route('/save_theme', methods=['POST'])
def save_theme():
    return jsonify({'success': True})

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'username' not in session: return jsonify({'error': 'Not logged'}), 401
    name = session['username']; data = request.json
    if data.get('avatar'): users[name]['avatar'] = data['avatar'][:2]
    if data.get('avatar_base64'): users[name]['avatar_base64'] = data['avatar_base64']
    if data.get('bio') is not None: users[name]['bio'] = data['bio'][:200]
    if data.get('new_name'):
        nn = data['new_name']
        if len(nn) < 3 or len(nn) > 20: return jsonify({'error': 'Имя 3-20'}), 400
        if nn in users and nn != name: return jsonify({'error': 'Имя занято'}), 400
        users[nn] = users.pop(name); session['username'] = nn
    if data.get('new_password') and len(data['new_password']) >= 4: users[session['username']]['password'] = hashlib.sha256(data['new_password'].encode()).hexdigest()
    save_users(users); return jsonify({'success': True})

@app.route('/change_id', methods=['POST'])
def change_id():
    if 'username' not in session: return jsonify({'error': 'Not logged'}), 401
    name = session['username']; new_id = request.json.get('new_id')
    if not new_id or not new_id.isdigit() or len(new_id) < 4 or len(new_id) > 8: return jsonify({'error': 'ID должен быть числом от 4 до 8 цифр'})
    u = users[name]
    if u.get('id_change_count', 0) == 0:
        u['user_id'] = new_id; u['id_change_count'] = 1; u['last_id_change'] = datetime.now().isoformat(); save_users(users); return jsonify({'success': True})
    else:
        last_change = datetime.fromisoformat(u['last_id_change']) if u.get('last_id_change') else None
        if last_change and datetime.now() - last_change < timedelta(days=14):
            next_change = last_change + timedelta(days=14)
            return jsonify({'error': f'Следующая смена ID с {next_change.strftime("%d.%m.%Y %H:%M")}'})
        u['user_id'] = new_id; u['last_id_change'] = datetime.now().isoformat(); save_users(users); return jsonify({'success': True})

@app.route('/id_change_info')
def id_change_info():
    if 'username' not in session: return jsonify({'can_change': False, 'next_change_date': ''})
    name = session['username']; u = users[name]
    if u.get('id_change_count', 0) == 0: return jsonify({'can_change': True, 'next_change_date': ''})
    last_change = datetime.fromisoformat(u['last_id_change']) if u.get('last_id_change') else None
    if last_change and datetime.now() - last_change < timedelta(days=14):
        next_change = last_change + timedelta(days=14)
        return jsonify({'can_change': False, 'next_change_date': next_change.strftime("%d.%m.%Y %H:%M")})
    return jsonify({'can_change': True, 'next_change_date': ''})

@app.route('/delete_room', methods=['POST'])
def delete_room():
    if 'username' not in session or users[session['username']]['role'] not in ['owner', 'admin']:
        return jsonify({'success': False, 'message': 'Нет прав'})
    room = request.json.get('room')
    if room in rooms and room != 'Главная':
        rooms.remove(room)
        if room in messages: del messages[room]
        save_rooms(rooms); save_messages(messages)
        socketio.emit('rooms', rooms, broadcast=True)
        return jsonify({'success': True, 'message': f'Комната "{room}" удалена'})
    return jsonify({'success': False, 'message': 'Нельзя удалить главную комнату'})

@app.route('/give_admin', methods=['POST'])
def give_admin():
    if 'username' not in session or users[session['username']]['role'] != 'owner': return jsonify({'message': 'Только владелец'})
    target = request.json.get('username')
    if target in users and users[target]['role'] != 'owner' and users[target]['role'] != 'admin':
        users[target]['role'] = 'admin'; save_users(users); socketio.emit('system', {'text': f'⭐ {target} назначен администратором!'}, broadcast=True); return jsonify({'message': f'{target} теперь админ'})
    return jsonify({'message': 'Не найден или уже админ'})

@app.route('/remove_admin', methods=['POST'])
def remove_admin():
    if 'username' not in session or users[session['username']]['role'] != 'owner': return jsonify({'message': 'Только владелец'})
    target = request.json.get('username')
    if target in users and users[target]['role'] == 'admin':
        users[target]['role'] = 'user'; save_users(users); socketio.emit('system', {'text': f'🔻 У {target} снята админка'}, broadcast=True); return jsonify({'message': f'У {target} снята админка'})
    return jsonify({'message': 'Не найден или не админ'})

@app.route('/mute_user', methods=['POST'])
def mute_user():
    if 'username' not in session or users[session['username']]['role'] not in ['owner', 'admin']: return jsonify({'message': 'Нет прав'})
    target = request.json.get('username'); minutes = int(request.json.get('minutes', 5))
    if target not in users or users[target]['role'] == 'owner': return jsonify({'message': 'Нельзя замутить владельца'})
    users[target]['muted_until'] = (datetime.now() + timedelta(minutes=minutes)).isoformat(); save_users(users)
    socketio.emit('system', {'text': f'🔇 {target} замучен на {minutes} минут'}, broadcast=True)
    return jsonify({'message': f'{target} замучен на {minutes} минут'})

@app.route('/unmute_user', methods=['POST'])
def unmute_user():
    if 'username' not in session or users[session['username']]['role'] not in ['owner', 'admin']: return jsonify({'message': 'Нет прав'})
    target = request.json.get('username')
    if target in users:
        users[target]['muted_until'] = None; save_users(users)
        socketio.emit('system', {'text': f'🔊 {target} размучен!'}, broadcast=True)
        return jsonify({'message': f'{target} размучен'})
    return jsonify({'message': 'Не найден'})

@app.route('/ban_user', methods=['POST'])
def ban_user():
    if 'username' not in session or users[session['username']]['role'] not in ['owner', 'admin']: return jsonify({'message': 'Нет прав'})
    target = request.json.get('username')
    if target not in users or users[target]['role'] == 'owner': return jsonify({'message': 'Нельзя забанить владельца'})
    users[target]['banned'] = True; save_users(users)
    socketio.emit('system', {'text': f'🔨 {target} забанен!'}, broadcast=True)
    return jsonify({'message': f'{target} забанен'})

@app.route('/unban_user', methods=['POST'])
def unban_user():
    if 'username' not in session or users[session['username']]['role'] not in ['owner', 'admin']: return jsonify({'message': 'Нет прав'})
    target = request.json.get('username')
    if target in users:
        users[target]['banned'] = False; save_users(users)
        socketio.emit('system', {'text': f'🔓 {target} разбанен!'}, broadcast=True)
        return jsonify({'message': f'{target} разбанен'})
    return jsonify({'message': 'Не найден'})

@app.route('/add_friend', methods=['POST'])
def add_friend():
    if 'username' not in session: return jsonify({'message': 'Войдите'})
    name = session['username']; target = request.json.get('friend')
    if target not in users: return jsonify({'message': 'Не найден'})
    if target == name: return jsonify({'message': 'Себя нельзя'})
    if target in friends.get(name, []): return jsonify({'message': 'Уже друг'})
    if name in friends.get(target, []): return jsonify({'message': 'Заявка уже отправлена'})
    friends.setdefault(target, []).append(name)
    save_friends(friends)
    socketio.emit('friend_request', {'from': name}, to=target)
    return jsonify({'message': f'Заявка отправлена {target}'})

@app.route('/accept_friend', methods=['POST'])
def accept_friend():
    if 'username' not in session: return jsonify({'message': 'Войдите'})
    name = session['username']; target = request.json.get('friend')
    if target not in friends.get(name, []): return jsonify({'message': 'Нет заявки'})
    friends[name].remove(target)
    friends.setdefault(name, []).append(target)
    friends.setdefault(target, []).append(name)
    save_friends(friends)
    return jsonify({'message': f'Вы приняли заявку от {target}'})

@app.route('/cancel_friend_request', methods=['POST'])
def cancel_friend_request():
    if 'username' not in session: return jsonify({'message': 'Войдите'})
    name = session['username']; target = request.json.get('friend')
    if target not in friends.get(name, []): return jsonify({'message': 'Нет исходящей заявки'})
    friends[name].remove(target)
    if name in friends.get(target, []): friends[target].remove(name)
    save_friends(friends)
    return jsonify({'message': f'Заявка для {target} отменена'})

@app.route('/remove_friend', methods=['POST'])
def remove_friend():
    if 'username' not in session: return jsonify({'message': 'Войдите'})
    name = session['username']; target = request.json.get('friend')
    if target in friends.get(name, []):
        friends[name].remove(target); friends[target].remove(name); save_friends(friends); return jsonify({'message': f'{target} удалён из друзей'})
    return jsonify({'message': 'Не в друзьях'})

@app.route('/get_friend_requests')
def get_friend_requests():
    if 'username' not in session: return jsonify({'requests': []})
    name = session['username']
    return jsonify({'requests': friends.get(name, [])})

@app.route('/clear_history', methods=['POST'])
def clear_history():
    if 'username' not in session: return jsonify({'success': False})
    global messages
    messages = {'Главная': []}
    save_messages(messages)
    return jsonify({'success': True})

@app.route('/export_chat')
def export_chat():
    if 'username' not in session: return jsonify({'error': 'Not logged'})
    import json
    data = json.dumps(messages, ensure_ascii=False, indent=2)
    return Response(data, mimetype='application/json', headers={'Content-Disposition': 'attachment;filename=chat_history.json'})

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'username' not in session: return jsonify({'error': 'Not logged'})
    new_pass = request.json.get('new_password')
    if not new_pass or len(new_pass) < 4: return jsonify({'error': 'Слишком короткий'})
    users[session['username']]['password'] = hashlib.sha256(new_pass.encode()).hexdigest()
    save_users(users)
    return jsonify({'success': True})

@app.route('/user_avatar/<name>')
def user_avatar(name):
    if name not in users: return jsonify({'avatar_base64': None})
    return jsonify({'avatar_base64': users[name].get('avatar_base64')})

@app.route('/user_info/<name>')
def user_info(name):
    if name not in users: return jsonify({'error': 'Not found'}), 404
    u = users[name]
    is_friend = name in friends.get(session.get('username', ''), []) if session.get('username') else False
    role_display = {'owner': 'Владелец', 'admin': 'Админ', 'user': 'Пользователь'}.get(u['role'], 'Пользователь')
    return jsonify({'username': name, 'bio': u.get('bio', ''), 'role_display': role_display, 'user_role': u['role'], 'avatar': u.get('avatar', '👤'), 'avatar_base64': u.get('avatar_base64'), 'user_id': u.get('user_id', ''), 'friends_count': len(friends.get(name, [])), 'is_friend': is_friend, 'banned': u.get('banned', False), 'muted': u.get('muted_until') and datetime.now() < datetime.fromisoformat(u['muted_until'])})

@app.route('/get_dm_list')
def get_dm_list():
    if 'username' not in session: return jsonify({'dms': []})
    name = session['username']; result = []
    for key, conv in dms.items():
        parts = key.split('_')
        if name in parts:
            other = parts[0] if parts[1] == name else parts[1]
            last = conv[-1] if conv else None
            result.append({'with': other, 'last_preview': last['text'][:30] if last else ''})
    return jsonify({'dms': result})

@app.route('/get_dm/<target>')
def get_dm(target):
    if 'username' not in session: return jsonify({'messages': []})
    name = session['username']; key = f"{min(name, target)}_{max(name, target)}"
    msgs = dms.get(key, [])
    for m in msgs:
        if 'timestamp' not in m:
            m['timestamp'] = datetime.now().timestamp()
    return jsonify({'messages': msgs})

# -------------------------- SOCKET.IO --------------------------

@socketio.on('connect')
def on_connect():
    username = session.get('username')
    if username and username in users and not users[username].get('banned'):
        users[username]['online'] = True
        save_users(users)
        emit('user_online', {'name': username}, broadcast=True)

@socketio.on('disconnect')
def on_disconnect():
    username = session.get('username')
    if username and username in users:
        users[username]['online'] = False
        save_users(users)
        emit('user_offline', {'name': username}, broadcast=True)

@socketio.on('private_message')
def private_message(data):
    username = session.get('username')
    if not username: return
    target = data['target']; text = data['text']
    key = f"{min(username, target)}_{max(username, target)}"
    msg = {'from': username, 'to': target, 'text': text, 'time': datetime.now().strftime('%H:%M'), 'timestamp': datetime.now().timestamp()}
    if key not in dms: dms[key] = []
    dms[key].append(msg); save_dms(dms)
    emit('private_message', msg, to=target); emit('private_message', msg, to=username)

@socketio.on('file_message')
def file_message(data):
    username = session.get('username')
    if not username or users.get(username, {}).get('banned'): return
    room = data['room']
    file_name = data['name']; file_data = data['data']; file_type = data['type']; is_image = data['isImage']
    msg_id = str(int(datetime.now().timestamp() * 1000))
    msg = {
        'id': msg_id,
        'name': username,
        'text': '',
        'time': datetime.now().strftime('%H:%M'),
        'avatar': users[username].get('avatar', '👤'),
        'avatar_base64': users[username].get('avatar_base64'),
        'file': {'name': file_name, 'data': file_data, 'type': file_type, 'isImage': is_image}
    }
    if room not in messages: messages[room] = []
    messages[room].append(msg)
    if len(messages[room]) > 100: messages[room] = messages[room][-100:]
    save_messages(messages)
    emit('file_message', msg, to=room, broadcast=True)

@socketio.on('delete_message')
def delete_message(data):
    username = session.get('username')
    if not username: return
    room = data['room']; msg_id = data['messageId']
    for i, m in enumerate(messages.get(room, [])):
        if str(m.get('id')) == msg_id:
            if m['name'] == username or users[username]['role'] in ['owner', 'admin']:
                messages[room].pop(i)
                save_messages(messages)
                emit('delete_message', {'messageId': msg_id}, to=room, broadcast=True)
            break

@socketio.on('join')
def on_join(data):
    username = session.get('username')
    if not username or users.get(username, {}).get('banned'): return
    room = data['room']; join_room(room); emit('history', messages.get(room, []), to=request.sid)

@socketio.on('message')
def on_message(data):
    username = session.get('username')
    if not username or users.get(username, {}).get('banned'): return
    u = users.get(username)
    if u.get('muted_until') and datetime.now() < datetime.fromisoformat(u['muted_until']):
        emit('system', {'text': '🔇 Вы замучены и не можете писать!'}, to=request.sid); return
    room = data['room']; text = data['text']
    msg_id = str(int(datetime.now().timestamp() * 1000))
    msg = {'id': msg_id, 'name': username, 'text': text, 'time': datetime.now().strftime('%H:%M'), 'avatar': users[username].get('avatar', '👤'), 'avatar_base64': users[username].get('avatar_base64')}
    if room not in messages: messages[room] = []
    messages[room].append(msg)
    if len(messages[room]) > 100: messages[room] = messages[room][-100:]
    save_messages(messages); emit('message', msg, to=room, broadcast=True)

@socketio.on('switch')
def on_switch(data):
    username = session.get('username')
    if not username: return
    old = data['old']; new = data['new']; leave_room(old); join_room(new); emit('history', messages.get(new, []), to=request.sid)

@socketio.on('create')
def on_create(data):
    username = session.get('username')
    if not username or users[username]['role'] not in ['owner', 'admin']: return
    new_room = data['room'].strip()
    if new_room and new_room not in rooms:
        rooms.append(new_room); messages[new_room] = []; save_rooms(rooms); save_messages(messages); emit('rooms', rooms, broadcast=True)

@socketio.on('typing')
def on_typing(data):
    username = session.get('username')
    if not username: return
    emit('typing', {'name': username, 'typing': data['typing']}, to=data['room'], broadcast=True, include_self=False)

@socketio.on('get_rooms')
def get_rooms(): emit('rooms', rooms)

@socketio.on('get_users')
def get_users():
    lst = []
    for name, u in users.items():
        if not u.get('banned') and u.get('online'):
            lst.append({'name': name, 'role': u['role'], 'avatar': u.get('avatar', '👤'), 'avatar_base64': u.get('avatar_base64')})
    emit('users', lst, broadcast=True)
    if session.get('username'):
        name = session['username']
        friends_list = [{'name': f} for f in friends.get(name, [])]
        emit('friends', friends_list, to=request.sid)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
