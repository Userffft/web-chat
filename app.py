import os
import json
import hashlib
import random
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, session, redirect, url_for, jsonify, send_file
from flask_socketio import SocketIO, emit, join_room, leave_room

DB_PATH = 'db'
os.makedirs(DB_PATH, exist_ok=True)

USERS_FILE = os.path.join(DB_PATH, 'users.json')
MESSAGES_FILE = os.path.join(DB_PATH, 'messages.json')
ROOMS_FILE = os.path.join(DB_PATH, 'rooms.json')
DMS_FILE = os.path.join(DB_PATH, 'dms.json')
REPORTS_FILE = os.path.join(DB_PATH, 'reports.json')
NOTIFS_FILE = os.path.join(DB_PATH, 'user_notifications.json')

app = Flask(__name__)
app.secret_key = 'secret-key-2024'
socketio = SocketIO(app, cors_allowed_origins="*")

online_users = set()

def short_id():
    return str(random.randint(1000, 99999999))

def load_json(path, default):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f)

users = load_json(USERS_FILE, {
    'MrAizex': {
        'password': hashlib.sha256('admin123'.encode()).hexdigest(),
        'role': 'owner',
        'avatar_base64': None,
        'bio': 'Владелец',
        'friends': [],
        'requests': [],
        'banned': False,
        'theme': 'light',
        'user_id': short_id(),
        'id_change_count': 0,
        'last_id_change': None,
        'muted_until': None
    },
    'dimooon': {
        'password': hashlib.sha256('1111'.encode()).hexdigest(),
        'role': 'admin',
        'avatar_base64': None,
        'bio': 'Админ',
        'friends': [],
        'requests': [],
        'banned': False,
        'theme': 'light',
        'user_id': short_id(),
        'id_change_count': 0,
        'last_id_change': None,
        'muted_until': None
    }
})
messages = load_json(MESSAGES_FILE, {'Главная': []})
rooms = load_json(ROOMS_FILE, ['Главная'])
dms = load_json(DMS_FILE, {})
reports = load_json(REPORTS_FILE, [])

def save_all():
    save_json(USERS_FILE, users)
    save_json(MESSAGES_FILE, messages)
    save_json(ROOMS_FILE, rooms)
    save_json(DMS_FILE, dms)
    save_json(REPORTS_FILE, reports)

def role_display(r):
    return {'owner':'Владелец','admin':'Администратор','moderator':'Модератор','user':'Пользователь'}.get(r,'Пользователь')

def load_user_notifs(username):
    if os.path.exists(NOTIFS_FILE):
        with open(NOTIFS_FILE, 'r') as f:
            all_n = json.load(f)
        return all_n.get(username, [])
    return []

def save_user_notifs(username, notifs):
    all_n = {}
    if os.path.exists(NOTIFS_FILE):
        with open(NOTIFS_FILE, 'r') as f:
            all_n = json.load(f)
    all_n[username] = notifs[-50:]
    with open(NOTIFS_FILE, 'w') as f:
        json.dump(all_n, f)

LOGIN_HTML = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes"><title>Чатик</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}.card{background:rgba(255,255,255,0.95);border-radius:48px;padding:40px;max-width:400px;width:100%;text-align:center;box-shadow:0 25px 50px -12px rgba(0,0,0,0.25)}h1{margin-bottom:8px;background:linear-gradient(135deg,#667eea,#764ba2);-webkit-background-clip:text;-webkit-text-fill-color:transparent}.subtitle{color:#6b7280;margin-bottom:32px}input{width:100%;padding:16px;border:2px solid #e5e7eb;border-radius:32px;margin-bottom:16px;outline:none}input:focus{border-color:#667eea}button{width:100%;padding:16px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border:none;border-radius:32px;cursor:pointer}.error{background:#fee2e2;color:#dc2626;padding:12px;border-radius:24px;margin-bottom:20px}.footer{margin-top:24px}a{color:#667eea}</style></head>
<body><div class="card"><h1>💬 Чатик</h1><div class="subtitle">Общайся с друзьями</div>{% if error %}<div class="error">{{ error }}</div>{% endif %}<form method="post"><input type="text" name="username" placeholder="Имя" required autofocus><input type="password" name="password" placeholder="Пароль" required><button type="submit">Войти</button></form><div class="footer">Нет аккаунта? <a href="/register">Регистрация</a></div></div></body>
</html>
'''

REGISTER_HTML = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes"><title>Чатик</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}.card{background:rgba(255,255,255,0.95);border-radius:48px;padding:40px;max-width:400px;width:100%;text-align:center;box-shadow:0 25px 50px -12px rgba(0,0,0,0.25)}h1{margin-bottom:32px;background:linear-gradient(135deg,#667eea,#764ba2);-webkit-background-clip:text;-webkit-text-fill-color:transparent}input{width:100%;padding:16px;border:2px solid #e5e7eb;border-radius:32px;margin-bottom:16px;outline:none}input:focus{border-color:#667eea}button{width:100%;padding:16px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border:none;border-radius:32px;cursor:pointer}.error{background:#fee2e2;color:#dc2626;padding:12px;border-radius:24px;margin-bottom:20px}.footer{margin-top:24px}a{color:#667eea}</style></head>
<body><div class="card"><h1>📝 Регистрация</h1>{% if error %}<div class="error">{{ error }}</div>{% endif %}<form method="post"><input type="text" name="username" placeholder="Имя (3-20)" required autofocus><input type="password" name="password" placeholder="Пароль (мин 4)" required><button type="submit">Создать</button></form><div class="footer">Уже есть? <a href="/login">Войти</a></div></div></body>
</html>
'''

CHAT_HTML = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes"><title>Чатик</title><script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script><style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:linear-gradient(135deg,#1e1b4b,#4c1d95);height:100vh;display:flex;overflow:hidden;transition:background 0.3s}body.dark{background:#0f0f0f}
.sidebar{width:280px;background:rgba(255,255,255,0.95);backdrop-filter:blur(10px);border-right:1px solid rgba(0,0,0,0.1);display:flex;flex-direction:column;overflow-y:auto;transition:0.3s;z-index:10}body.dark .sidebar{background:#1a1a1a;color:#fff;border-color:#333}
.user-card{text-align:center;padding:24px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;cursor:pointer;margin-bottom:16px;transition:transform 0.2s}.user-card:active{transform:scale(0.98)}body.dark .user-card{background:linear-gradient(135deg,#4f46e5,#6d28d9)}
.user-avatar{width:64px;height:64px;border-radius:50%;margin:0 auto 10px;background:rgba(255,255,255,0.2);display:flex;align-items:center;justify-content:center;font-size:36px;overflow:hidden}.user-avatar img{width:100%;height:100%;object-fit:cover}
.user-name{font-size:18px;font-weight:700}.user-bio{font-size:11px;opacity:0.85;margin-top:5px}.user-id{font-size:9px;opacity:0.6;margin-top:3px}
.section-title{font-weight:600;padding:16px 20px 8px 20px;color:#475569;font-size:12px;text-transform:uppercase}body.dark .section-title{color:#94a3b8}
.room-item,.user-item{padding:12px 20px;margin:4px 12px;border-radius:16px;cursor:pointer;display:flex;align-items:center;gap:12px;transition:0.2s}.room-item:hover,.user-item:hover{background:rgba(0,0,0,0.05)}body.dark .room-item:hover,body.dark .user-item:hover{background:rgba(255,255,255,0.1)}.room-item.active{background:#4f46e5;color:#fff}.delete-room{background:#ef4444;border:none;border-radius:20px;padding:4px 8px;color:#fff;margin-left:auto;cursor:pointer;font-size:10px;transition:0.1s}.delete-room:active{transform:scale(0.9)}
.add-room{display:flex;gap:8px;margin:12px}.add-room input{flex:1;padding:10px;border-radius:40px;border:1px solid #ddd;outline:none;transition:0.2s}body.dark .add-room input{background:#333;color:#fff;border-color:#555}.add-room input:focus{border-color:#4f46e5}.add-room button{background:#4f46e5;color:#fff;border:none;border-radius:40px;padding:8px 20px;cursor:pointer;transition:0.1s}.add-room button:active{transform:scale(0.95)}
.chat-area{flex:1;display:flex;flex-direction:column;background:#fff;transition:0.3s}body.dark .chat-area{background:#0a0a0a}
.chat-header{padding:12px 20px;background:#fff;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}body.dark .chat-header{background:#1a1a1a;border-color:#333;color:#fff}
.top-bar{display:flex;align-items:center;gap:15px;flex-wrap:wrap}
.users-count{background:#4f46e5;padding:4px 10px;border-radius:20px;font-size:12px;color:#fff;transition:0.1s;cursor:default}
.menu-btn{display:none;font-size:24px;background:none;border:none;cursor:pointer;padding:8px 12px;color:#333}body.dark .menu-btn{color:#fff}
.messages{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:8px}
@keyframes fadeSlide{from{opacity:0;transform:translateY(8px) scale(0.98)}to{opacity:1;transform:translateY(0) scale(1)}}
.message{display:flex;gap:10px;align-items:flex-start;margin-bottom:8px;animation:fadeSlide 0.2s ease-out}
.message-own{justify-content:flex-end}
.skeleton{display:flex;gap:10px;align-items:center;padding:8px;background:rgba(0,0,0,0.03);border-radius:20px;animation:pulse 1.2s infinite}body.dark .skeleton{background:rgba(255,255,255,0.05)}
@keyframes pulse{0%{opacity:0.6}50%{opacity:1}100%{opacity:0.6}}
.skeleton-avatar{width:36px;height:36px;background:#ddd;border-radius:50%}body.dark .skeleton-avatar{background:#333}
.skeleton-text{flex:1;height:40px;background:#ddd;border-radius:20px}body.dark .skeleton-text{background:#333}
.message-avatar{width:36px;height:36px;border-radius:50%;background:#4f46e5;display:flex;align-items:center;justify-content:center;font-size:16px;cursor:pointer;flex-shrink:0;overflow:hidden;transition:0.1s}.message-avatar:active{transform:scale(0.9)}
.message-avatar img{width:100%;height:100%;object-fit:cover}
.message-content{background:#f1f5f9;padding:8px 12px;border-radius:18px;max-width:65%;word-break:break-word;position:relative;display:flex;flex-direction:column;transition:0.1s}body.dark .message-content{background:#2a2a2a;color:#e2e8f0}.message-own .message-content{background:#4f46e5;color:#fff}
.message-name{font-weight:700;font-size:12px;display:flex;align-items:center;gap:6px;margin-bottom:2px}
.message-time-align{display:flex;justify-content:flex-end;margin-top:4px}
.message-time{font-size:9px;opacity:0.6}
.message-text{margin-top:2px;font-size:14px;line-height:1.4}
.message-actions{position:absolute;right:-28px;top:4px;display:flex;gap:4px;opacity:0;transition:0.2s}.message:hover .message-actions{opacity:1}
.delete-msg{background:#374151;border:none;border-radius:50%;width:24px;height:24px;color:#fff;cursor:pointer;font-size:12px;display:flex;align-items:center;justify-content:center;transition:0.1s}.delete-msg:active{transform:scale(0.9)}
.badge-owner{background:#ef4444;font-size:8px;padding:2px 6px;border-radius:20px}
.badge-admin{background:#10b981;font-size:8px;padding:2px 6px;border-radius:20px}
.badge-moderator{background:#f59e0b;font-size:8px;padding:2px 6px;border-radius:20px}
.online-dot{width:8px;height:8px;background:#10b981;border-radius:50%;display:inline-block;margin-right:8px;box-shadow:0 0 3px #10b981}
.system-msg{text-align:center;font-size:11px;color:#64748b;padding:6px;margin:4px 0;animation:fadeSlide 0.2s ease-out}
.typing{padding:6px 24px;font-size:11px;color:#64748b;font-style:italic;animation:pulse 1.2s infinite}
.input-area{display:flex;gap:12px;padding:12px 20px;background:#fff;border-top:1px solid #eee;transition:0.3s}body.dark .input-area{background:#1a1a1a;border-color:#333}
.input-area input{flex:1;padding:12px 16px;border:2px solid #e2e8f0;border-radius:40px;outline:none;font-size:14px;transition:0.2s}body.dark .input-area input{background:#2a2a2a;color:#fff;border-color:#444}.input-area input:focus{border-color:#4f46e5}
.input-area button{background:#4f46e5;border:none;border-radius:50%;width:44px;height:44px;color:#fff;cursor:pointer;font-size:18px;display:flex;align-items:center;justify-content:center;transition:0.1s}.input-area button:active{transform:scale(0.95)}.input-area button:disabled{opacity:0.5;transform:none}
.btn-settings,.btn-logout{margin:8px 12px;padding:12px;border-radius:20px;cursor:pointer;border:none;font-weight:500;transition:0.1s}.btn-settings:active,.btn-logout:active{transform:scale(0.97)}.btn-settings{background:#e0e7ff;color:#4f46e5}body.dark .btn-settings{background:#2a2a2a;color:#818cf8}.btn-logout{background:#fee2e2;color:#dc2626}body.dark .btn-logout{background:#2a2a2a;color:#f87171}
.modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);align-items:center;justify-content:center;z-index:1000;animation:fadeSlide 0.15s ease-out}.modal-content{background:#fff;border-radius:28px;padding:24px;max-width:500px;width:90%;max-height:80vh;overflow-y:auto}body.dark .modal-content{background:#1a1a1a;color:#fff}.modal-content input,.modal-content textarea,.modal-content select{width:100%;padding:12px;margin:8px 0;border-radius:24px;border:1px solid #ddd;outline:none}body.dark .modal-content input,body.dark .modal-content textarea,body.dark .modal-content select{background:#2a2a2a;border-color:#444;color:#fff}.modal-content button{background:#4f46e5;color:#fff;border:none;padding:12px;border-radius:24px;width:100%;cursor:pointer;margin-top:8px;transition:0.1s}.modal-content button:active{transform:scale(0.98)}.close{float:right;font-size:24px;cursor:pointer}
.emoji-picker{position:absolute;bottom:80px;left:20px;background:#fff;border-radius:20px;padding:12px;display:none;grid-template-columns:repeat(6,1fr);gap:8px;box-shadow:0 10px 25px rgba(0,0,0,0.15);z-index:1000;animation:fadeSlide 0.1s ease-out}body.dark .emoji-picker{background:#1a1a1a}.emoji{font-size:28px;cursor:pointer;text-align:center;padding:6px;border-radius:12px;transition:0.1s}.emoji:active{transform:scale(0.9)}
.notify-btn{position:relative;background:none;border:none;cursor:pointer;font-size:20px;padding:8px;border-radius:50%;transition:0.1s}.notify-btn:active{transform:scale(0.9)}.notify-badge{position:absolute;top:-2px;right:-2px;background:#ef4444;color:#fff;font-size:10px;min-width:18px;height:18px;border-radius:20px;display:none;align-items:center;justify-content:center}
.friend-request-item{display:flex;justify-content:space-between;align-items:center;padding:12px;margin:8px 0;background:#f1f5f9;border-radius:20px}body.dark .friend-request-item{background:#2a2a2a}
.profile-avatar{width:100px;height:100px;border-radius:50%;margin:0 auto 12px;background:#e2e8f0;display:flex;align-items:center;justify-content:center;font-size:48px;overflow:hidden}.profile-avatar img{width:100%;height:100%;object-fit:cover}
.profile-name{font-size:20px;font-weight:700;text-align:center;margin-bottom:4px}.profile-role{text-align:center;font-size:12px;color:#6b7280;margin-bottom:8px}.profile-id{text-align:center;font-size:11px;color:#94a3b8;margin-bottom:16px;font-family:monospace;cursor:pointer}.profile-bio{background:#f1f5f9;padding:12px;border-radius:20px;margin:16px 0;font-size:14px}body.dark .profile-bio{background:#2a2a2a}
.profile-actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:16px}.profile-actions button{flex:1;padding:10px;border-radius:24px;border:none;cursor:pointer;font-weight:500;transition:0.1s}.profile-actions button:active{transform:scale(0.97)}
.toast{position:fixed;bottom:20px;right:20px;background:#4f46e5;color:#fff;padding:12px 20px;border-radius:40px;z-index:2000;animation:slideIn 0.3s;box-shadow:0 5px 15px rgba(0,0,0,0.2)}@keyframes slideIn{from{transform:translateX(100%);opacity:0}to{transform:translateX(0);opacity:1}}
.file-message{background:rgba(79,70,229,0.1);padding:6px 10px;border-radius:16px;display:inline-flex;align-items:center;gap:8px}
.image-preview{max-width:180px;max-height:180px;border-radius:12px;cursor:pointer;margin-top:4px;transition:0.1s}.image-preview:active{transform:scale(0.98)}
.audio-player{max-width:200px;margin-top:4px}
.report-item{padding:8px;border-bottom:1px solid #ddd;margin:5px 0;background:#f1f5f9;border-radius:16px}
.offline-user-item{display:flex;align-items:center;gap:12px;padding:8px;border-bottom:1px solid #eee}
.overlay{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:5}
@media(max-width:680px){
.sidebar{position:fixed;left:-280px;height:100%;z-index:20;transition:0.3s}.sidebar.open{left:0}.overlay{display:block}.menu-btn{display:block}.chat-header{padding:8px 12px}.message-content{max-width:80%}.user-card{padding:16px}
}
</style>
</head>
<body>
<div class="overlay" id="overlay"></div>
<div class="sidebar" id="sidebar">
    <div class="user-card" id="profileBtn">
        <div class="user-avatar">{% if avatar_base64 %}<img src="{{ avatar_base64 }}">{% else %}👤{% endif %}</div>
        <div class="user-name">{{ username }}{% if role == "owner" %}<span class="badge-owner"> ВЛ</span>{% elif role == "admin" %}<span class="badge-admin"> АДМ</span>{% elif role == "moderator" %}<span class="badge-moderator"> МОД</span>{% endif %}</div>
        <div class="user-bio">{{ bio[:40] }}</div>
        <div class="user-id">ID: {{ user_id }}</div>
    </div>
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
        <button class="menu-btn" id="menuBtn">☰</button>
        <div class="top-bar">
            <span id="roomName">Главная</span>
            <span class="users-count" id="regUsersCount">👥 Всего: 0</span>
        </div>
        <div style="display:flex; gap:8px;">
            <button class="notify-btn" id="notifyBtn"><span class="notify-badge" id="notifyBadge">0</span>🔔</button>
            {% if role in ["owner", "admin"] %}<button id="reportsBtn" class="notify-btn" style="background:#f59e0b;">⚠️ Жалобы</button>{% endif %}
        </div>
    </div>
    <div id="messagesList" class="messages"></div>
    <div id="typingStatus" class="typing"></div>
    <div class="input-area">
        <button id="emojiBtn">😊</button>
        <button id="fileBtn">📎</button>
        <button id="voiceBtn">🎙️</button>
        <input type="text" id="messageInput" placeholder="Сообщение...">
        <button id="sendBtn">📤</button>
        <input type="file" id="fileInput" style="display:none" accept="image/*,application/pdf,text/plain">
        <input type="file" id="avatarFileInput" style="display:none" accept="image/jpeg,image/png">
    </div>
</div>

<!-- Модалки -->
<div id="emojiPicker" class="emoji-picker"></div>
<div id="profileModal" class="modal"><div class="modal-content"><span class="close" id="closeProfile">&times;</span><h3>👤 Мой профиль</h3><button id="uploadAvatarBtn" style="background:#4f46e5;color:#fff">📷 Загрузить фото</button><div id="avatarPreview" class="profile-avatar" style="width:80px;height:80px;margin:10px auto;"></div><label>О себе:</label><textarea id="bioInput" rows="3">{{ bio }}</textarea><label>Новое имя:</label><input type="text" id="newName"><label>Новый пароль:</label><input type="password" id="newPass"><div id="idChangeInfo"></div><button id="changeIdBtn">🆔 Сменить ID</button><button id="saveProfile">💾 Сохранить</button></div></div>
<div id="settingsModal" class="modal"><div class="modal-content"><span class="close" id="closeSettings">&times;</span><h3>⚙️ Настройки</h3><button id="themeBtn">🌙 Тёмная тема</button></div></div>
<div id="notifyModal" class="modal"><div class="modal-content"><span class="close" id="closeNotifyModal">&times;</span><h3>🔔 Уведомления</h3><div id="notificationsList"></div></div></div>
<div id="userModal" class="modal"><div class="modal-content"><span class="close" id="closeUserModal">&times;</span><div id="userModalContent"></div></div></div>
<div id="reportsModal" class="modal"><div class="modal-content"><span class="close" id="closeReportsModal">&times;</span><h3>⚠️ Жалобы</h3><div id="reportsList"></div></div></div>
<div id="previewModal" class="modal"><div class="modal-content"><span class="close" id="closePreview">&times;</span><h3>Предпросмотр</h3><div id="previewContent"></div><div style="display:flex;gap:10px;margin-top:16px"><button id="confirmSend" style="background:#10b981;">Отправить</button><button id="cancelSend" style="background:#ef4444;">Отмена</button></div></div></div>

<!-- Полноэкранные ЛС -->
<div id="fullscreenDm" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.95); z-index:2000; flex-direction:column;">
    <div style="padding:15px; background:#1e293b; color:#fff; display:flex; align-items:center; gap:15px;">
        <button id="closeFullscreenDm" style="background:none; border:none; color:#fff; font-size:24px; cursor:pointer;">← Назад</button>
        <span id="fsDmTargetName" style="font-size:18px;"></span>
    </div>
    <div id="fsDmMessages" style="flex:1; overflow-y:auto; padding:20px; background:#0f172a;"></div>
    <div style="padding:15px; background:#1e293b; display:flex; gap:10px;">
        <input type="text" id="fsDmInput" placeholder="Сообщение..." style="flex:1; padding:12px; border-radius:40px; border:none;">
        <button id="fsDmSendBtn" style="background:#4f46e5; color:#fff; border:none; border-radius:40px; padding:12px 20px;">📤</button>
    </div>
</div>

<script>
let socket=io(),currentRoom='Главная',username='{{ username }}',role='{{ role }}',user_id='{{ user_id }}',typingUsers={};
let notifications=[],pendingFriendRequests=[],currentDMTarget=null;
let mediaRecorder=null,audioChunks=[],isRecording=false;
const msgDiv=document.getElementById('messagesList'),msgInput=document.getElementById('messageInput');
const sidebar=document.getElementById('sidebar'),overlay=document.getElementById('overlay');
document.getElementById('menuBtn').onclick=()=>{sidebar.classList.toggle('open');overlay.style.display=sidebar.classList.contains('open')?'block':'none';};
overlay.onclick=()=>{sidebar.classList.remove('open');overlay.style.display='none';};

function showToast(msg,type='success'){
    let t=document.createElement('div');t.className='toast';t.style.background=type==='success'?'#10b981':(type==='error'?'#ef4444':'#4f46e5');t.innerHTML=msg;document.body.appendChild(t);setTimeout(()=>t.remove(),3000);
}
const savedTheme = localStorage.getItem('chatTheme');
if(savedTheme === 'dark') document.body.classList.add('dark');
document.getElementById('themeBtn').onclick=()=>{
    document.body.classList.toggle('dark');
    localStorage.setItem('chatTheme',document.body.classList.contains('dark')?'dark':'light');
};
function addNotification(title,text){
    notifications.unshift({title,text,time:new Date().toLocaleTimeString()});
    if(notifications.length>20) notifications.pop();
    updateBadge(); updateNotifList();
    fetch('/add_notification',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title,text})});
}
function updateBadge(){
    let b=document.getElementById('notifyBadge');
    let c=notifications.length+pendingFriendRequests.length;
    if(c>0){b.textContent=c>99?'99+':c;b.style.display='flex';} else b.style.display='none';
}
function updateNotifList(){
    let c=document.getElementById('notificationsList');
    if(notifications.length===0&&pendingFriendRequests.length===0){c.innerHTML='<p style="color:#6b7280;text-align:center;padding:16px">Нет уведомлений</p>';return;}
    let h='';
    pendingFriendRequests.forEach(r=>{h+=`<div class="friend-request-item"><span>📨 Заявка от ${escape(r)}</span><button onclick="acceptReq('${escape(r)}')" style="background:#10b981;border:none;border-radius:20px;padding:6px 14px;color:#fff;cursor:pointer">Принять</button></div>`;});
    notifications.forEach(n=>{h+=`<div class="friend-request-item"><div><strong>${escape(n.title)}</strong><br><small>${escape(n.text)}</small><br><span style="font-size:10px">${n.time}</span></div></div>`;});
    c.innerHTML=h;
}
function loadRequests(){fetch('/get_requests').then(r=>r.json()).then(data=>{pendingFriendRequests=data.requests||[];updateBadge();updateNotifList();});}
document.getElementById('notifyBtn').onclick=()=>{document.getElementById('notifyModal').style.display='flex';updateNotifList();};
document.getElementById('closeNotifyModal').onclick=()=>document.getElementById('notifyModal').style.display='none';
fetch('/get_notifications').then(r=>r.json()).then(data=>{notifications=data;updateBadge();updateNotifList();});
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
        let r=new FileReader();
        r.onload=ev=>{tempAvatarBase64=ev.target.result;document.getElementById('avatarPreview').innerHTML=`<img src="${tempAvatarBase64}" style="width:100%;height:100%;object-fit:cover;">`;showToast('✅ Изображение выбрано, сохраните профиль','success');};
        r.readAsDataURL(file);
    }else showToast('❌ Выберите изображение','error');
    e.target.value='';
};
function showPreview(content,onConfirm){
    let modal=document.getElementById('previewModal');
    let previewDiv=document.getElementById('previewContent');
    previewDiv.innerHTML=content;
    let confirmBtn=document.getElementById('confirmSend');
    let cancelBtn=document.getElementById('cancelSend');
    let newConfirm=confirmBtn.cloneNode(true);
    let newCancel=cancelBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirm,confirmBtn);
    cancelBtn.parentNode.replaceChild(newCancel,cancelBtn);
    newConfirm.onclick=()=>{onConfirm(true);modal.style.display='none';};
    newCancel.onclick=()=>{onConfirm(false);modal.style.display='none';};
    modal.style.display='flex';
}
document.getElementById('fileBtn').onclick=()=>document.getElementById('fileInput').click();
document.getElementById('fileInput').onchange=function(e){
    let file=e.target.files[0];
    if(!file)return;
    let r=new FileReader();
    r.onload=ev=>{
        let data=ev.target.result;
        let isImage=file.type.startsWith('image/');
        let preview=isImage?`<img src="${data}" style="max-width:100%;max-height:300px;border-radius:12px;">`:`<div class="file-message"><span>📄</span> ${escape(file.name)}</div>`;
        showPreview(preview,(confirmed)=>{
            if(confirmed){
                socket.emit('file_message',{name:file.name,data:data,type:file.type,isImage:isImage,room:currentRoom});
                showToast('📁 Файл отправлен','success');
            }else showToast('❌ Отправка отменена','info');
        });
    };
    r.readAsDataURL(file);
    e.target.value='';
};
const voiceBtn=document.getElementById('voiceBtn');
voiceBtn.onclick=async()=>{
    if(isRecording){
        mediaRecorder.stop();
        isRecording=false;
        voiceBtn.style.background='#4f46e5';
        showToast('⏹️ Запись остановлена','info');
    }else{
        try{
            const stream=await navigator.mediaDevices.getUserMedia({audio:true});
            mediaRecorder=new MediaRecorder(stream);
            audioChunks=[];
            mediaRecorder.ondataavailable=e=>audioChunks.push(e.data);
            mediaRecorder.onstop=()=>{
                const blob=new Blob(audioChunks,{type:'audio/webm'});
                const r=new FileReader();
                r.onload=()=>{
                    let audioData=r.result;
                    showPreview(`<audio controls src="${audioData}" style="width:100%"></audio>`,(confirmed)=>{
                        if(confirmed){
                            socket.emit('voice_message',{data:audioData,room:currentRoom});
                            showToast('🎤 Голосовое отправлено','success');
                        }else showToast('❌ Отправка отменена','info');
                    });
                };
                r.readAsDataURL(blob);
                stream.getTracks().forEach(t=>t.stop());
            };
            mediaRecorder.start();
            isRecording=true;
            voiceBtn.style.background='#ef4444';
            showToast('🔴 Запись началась...','info');
        }catch(err){showToast('❌ Нет доступа к микрофону','error');}
    }
};
function loadDMList(){
    fetch('/get_dm_list').then(r=>r.json()).then(data=>{
        let c=document.getElementById('dmList');
        if(data.dms&&data.dms.length){
            c.innerHTML=data.dms.map(d=>`<div class="user-item" onclick="openDM('${escape(d.with)}')"><span>💬 ${escape(d.with)}</span><span style="font-size:10px">${escape(d.last_preview)}</span></div>`).join('');
        }else c.innerHTML='<div class="user-item">Нет диалогов</div>';
    });
}
function openDM(target){
    currentDMTarget=target;
    document.getElementById('fsDmTargetName').innerText=target;
    let container=document.getElementById('fsDmMessages');
    fetch('/get_dm/'+encodeURIComponent(target)).then(r=>r.json()).then(data=>{
        container.innerHTML=data.messages.map(m=>`<div style="margin:8px 0;text-align:${m.from===username?'right':'left'}"><div style="display:inline-block;background:${m.from===username?'#4f46e5':'#e2e8f0'};color:${m.from===username?'#fff':'#1f2937'};padding:8px 12px;border-radius:20px;max-width:80%"><strong>${escape(m.from)}</strong> (${m.time})<br>${escape(m.text)}</div></div>`).join('');
        container.scrollTop=container.scrollHeight;
    });
    document.getElementById('fullscreenDm').style.display='flex';
}
document.getElementById('closeFullscreenDm').onclick=()=>document.getElementById('fullscreenDm').style.display='none';
document.getElementById('fsDmSendBtn').onclick=()=>{
    let txt=document.getElementById('fsDmInput').value.trim();
    if(txt&&currentDMTarget){
        socket.emit('private_message',{target:currentDMTarget,text:txt});
        document.getElementById('fsDmInput').value='';
    }
};
socket.on('private_message',(data)=>{
    if(data.from===currentDMTarget||data.to===currentDMTarget){
        let c=document.getElementById('fsDmMessages');
        let d=document.createElement('div');
        d.style=`margin:8px 0;text-align:${data.from===username?'right':'left'}`;
        d.innerHTML=`<div style="display:inline-block;background:${data.from===username?'#4f46e5':'#e2e8f0'};color:${data.from===username?'#fff':'#1f2937'};padding:8px 12px;border-radius:20px;max-width:80%"><strong>${escape(data.from)}</strong> (${data.time})<br>${escape(data.text)}</div>`;
        c.appendChild(d);
        c.scrollTop=c.scrollHeight;
    }
    addNotification('Личное сообщение',`${data.from}: ${data.text.substring(0,30)}`);
    loadDMList();
});
const emojis=['😀','😂','❤️','👍','🎉','🔥','😍','🥹','😭','🤔','👋','🙏','✨','💯','😎','🥳'];
const picker=document.getElementById('emojiPicker');
picker.innerHTML=emojis.map(e=>`<div class="emoji">${e}</div>`).join('');
document.querySelectorAll('.emoji').forEach(el=>el.onclick=()=>{msgInput.value+=el.textContent;msgInput.focus();picker.style.display='none';});
document.getElementById('emojiBtn').onclick=(e)=>{e.stopPropagation();picker.style.display=picker.style.display==='grid'?'none':'grid';};
document.addEventListener('click',(e)=>{if(!e.target.closest('#emojiBtn')&&!e.target.closest('.emoji-picker'))picker.style.display='none';});
function showUserProfile(name){
    fetch('/user_info/'+encodeURIComponent(name)).then(r=>r.json()).then(data=>{
        let actions=`
            <button onclick="reportUser('${name}')" style="background:#ef4444;color:#fff">⚠️ Пожаловаться</button>
            ${role==='owner'||role==='admin'?`<button id="givePrivilegeBtn" style="background:#10b981;color:#fff">⭐ Выдать привилегию</button><button id="removePrivilegeBtn" style="background:#f59e0b;color:#fff">🔻 Снять привилегию</button>`:''}
        `;
        let avatarHtml=data.avatar_base64?`<img src="${data.avatar_base64}">`:'👤';
        document.getElementById('userModalContent').innerHTML=`
            <div class="profile-avatar">${avatarHtml}</div>
            <div class="profile-name">${escape(data.username)}</div>
            <div class="profile-role">${data.role_display}</div>
            <div class="profile-id" onclick="copyId('${data.user_id}')">🆔 ID: ${escape(data.user_id)} (скопировать)</div>
            <div class="profile-bio">📝 ${escape(data.bio||'Нет описания')}</div>
            <div class="profile-actions" id="profileActions">${actions}</div>
        `;
        document.getElementById('userModal').style.display='flex';
        if(role==='owner'||role==='admin'){
            document.getElementById('givePrivilegeBtn').onclick=()=>openRoleModal(name,'give');
            document.getElementById('removePrivilegeBtn').onclick=()=>openRoleModal(name,'remove');
        }
    });
}
function reportUser(target){
    let reason=prompt('Причина жалобы:');
    if(reason) fetch('/report_user',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({target,reason})}).then(r=>r.json()).then(d=>showToast(d.message,d.success?'success':'error'));
}
function openRoleModal(target,action){
    let modalHtml=`
        <div class="modal-content" style="max-width:300px;">
            <span class="close" id="closePrivilegeModal">&times;</span>
            <h3>${action==='give'?'Выдать привилегию':'Снять привилегию'}</h3>
            <select id="roleSelect" style="width:100%;padding:8px;margin:10px 0;">
                <option value="admin">Администратор</option>
                <option value="moderator">Модератор</option>
            </select>
            <button id="confirmPrivilege">Подтвердить</button>
        </div>
    `;
    let m=document.createElement('div');m.className='modal';m.style.display='flex';m.innerHTML=modalHtml;
    document.body.appendChild(m);
    m.querySelector('#closePrivilegeModal').onclick=()=>m.remove();
    m.querySelector('#confirmPrivilege').onclick=()=>{
        let newRole=m.querySelector('#roleSelect').value;
        let url=action==='give'?'/give_role':'/remove_role';
        fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:target,role:newRole})})
        .then(r=>r.json()).then(data=>{showToast(data.message,data.success?'success':'error');m.remove();if(data.success)location.reload();});
    };
}
window.copyId=id=>{navigator.clipboard.writeText(id);showToast('✅ ID скопирован','success');};
document.getElementById('reportsBtn')?.addEventListener('click',()=>{
    fetch('/get_reports').then(r=>r.json()).then(data=>{
        let listDiv=document.getElementById('reportsList');
        if(!data.reports.length) listDiv.innerHTML='<p>Нет жалоб</p>';
        else listDiv.innerHTML=data.reports.map(r=>`<div class="report-item"><b>От:</b> ${escape(r.from)}<br><b>На:</b> ${escape(r.target)}<br><b>Причина:</b> ${escape(r.reason)}<br><b>Время:</b> ${r.time}<br><button onclick="resolveReport(${r.id})">✅ Разобрано</button></div>`).join('');
        document.getElementById('reportsModal').style.display='flex';
    });
});
window.resolveReport=id=>{
    fetch('/resolve_report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})}).then(r=>r.json()).then(d=>{showToast(d.message);document.getElementById('reportsBtn').click();});
};
document.getElementById('closeReportsModal').onclick=()=>document.getElementById('reportsModal').style.display='none';
function updateAllUsersCount(){
    fetch('/registered_users_count').then(r=>r.json()).then(data=>{document.getElementById('regUsersCount').innerText=`👥 Всего: ${data.count}`;});
}
// Скелетон при загрузке сообщений
function showSkeleton(){
    for(let i=0;i<3;i++){
        let skel=document.createElement('div');skel.className='skeleton';
        skel.innerHTML=`<div class="skeleton-avatar"></div><div class="skeleton-text"></div>`;
        msgDiv.appendChild(skel);
    }
}
function hideSkeleton(){document.querySelectorAll('.skeleton').forEach(s=>s.remove());}
function addAudioMessage(id,name,audio,time,isOwn,avatar,avb){
    let div=document.createElement('div');div.className=`message ${isOwn?'message-own':''}`;div.dataset.id=id;
    let badge='';if(name==='MrAizex')badge='<span class="badge-owner">ВЛ</span>';else if(name==='dimooon')badge='<span class="badge-admin">АДМ</span>';
    let ahtml=avb?`<img src="${avb}">`:avatar||'👤';
    div.innerHTML=`
        <div class="message-avatar" onclick="showUserProfile('${escape(name)}')">${ahtml}</div>
        <div class="message-content">
            <div class="message-name">${escape(name)}${badge}</div>
            <div class="message-text"><audio class="audio-player" controls src="${audio}"></audio></div>
            <div class="message-time-align"><span class="message-time">${time}</span></div>
            <div class="message-actions">${(isOwn||role==='owner'||role==='admin')?`<button class="delete-msg" onclick="deleteMessage('${id}')">🗑</button>`:''}</div>
        </div>
    `;
    msgDiv.appendChild(div);msgDiv.scrollTop=msgDiv.scrollHeight;
}
function addMessage(id,name,text,time,isOwn,avatar,avb,isFile,fdata,fname,isImg,isVoice,vdata){
    let div=document.createElement('div');div.className=`message ${isOwn?'message-own':''}`;div.dataset.id=id;
    let badge='';if(name==='MrAizex')badge='<span class="badge-owner">ВЛ</span>';else if(name==='dimooon')badge='<span class="badge-admin">АДМ</span>';
    let ahtml=avb?`<img src="${avb}">`:avatar||'👤';
    let content='';
    if(isVoice) content=`<audio class="audio-player" controls src="${vdata}"></audio>`;
    else if(isFile){if(isImg) content=`<div><img src="${fdata}" class="image-preview" onclick="window.open('${fdata}')"></div>`; else content=`<div class="file-message"><span>📄</span><a href="${fdata}" download="${escape(fname)}">${escape(fname)}</a></div>`;}
    else content=escape(text);
    div.innerHTML=`
        <div class="message-avatar" onclick="showUserProfile('${escape(name)}')">${ahtml}</div>
        <div class="message-content">
            <div class="message-name">${escape(name)}${badge}</div>
            <div class="message-text">${content}</div>
            <div class="message-time-align"><span class="message-time">${time}</span></div>
            <div class="message-actions">${(isOwn||role==='owner'||role==='admin')?`<button class="delete-msg" onclick="deleteMessage('${id}')">🗑</button>`:''}</div>
        </div>
    `;
    msgDiv.appendChild(div);msgDiv.scrollTop=msgDiv.scrollHeight;
}
function deleteMessage(msgId){socket.emit('delete_message',{messageId:msgId,room:currentRoom});showToast('🗑️ Сообщение удалено','info');}
function escape(s){return s.replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'})[m]);}
showSkeleton();
socket.emit('join',{room:currentRoom});
socket.on('history',h=>{hideSkeleton();msgDiv.innerHTML='';h.forEach(m=>{
    if(m.voice) addAudioMessage(m.id,m.name,m.voice,m.time,m.name===username,m.avatar,m.avatar_base64);
    else if(m.file) addMessage(m.id,m.name,'',m.time,m.name===username,m.avatar,m.avatar_base64,true,m.file.data,m.file.name,m.file.isImage);
    else addMessage(m.id,m.name,m.text,m.time,m.name===username,m.avatar,m.avatar_base64);
});});
socket.on('message',m=>{
    if(m.voice) addAudioMessage(m.id,m.name,m.voice,m.time,m.name===username,m.avatar,m.avatar_base64);
    else if(m.file) addMessage(m.id,m.name,'',m.time,m.name===username,m.avatar,m.avatar_base64,true,m.file.data,m.file.name,m.file.isImage);
    else addMessage(m.id,m.name,m.text,m.time,m.name===username,m.avatar,m.avatar_base64);
});
socket.on('voice_message',m=>addAudioMessage(m.id,m.name,m.data,m.time,m.name===username,m.avatar,m.avatar_base64));
socket.on('delete_message',data=>{document.querySelectorAll(`.message[data-id="${data.messageId}"]`).forEach(el=>el.remove());showToast('🗑️ Сообщение удалено','info');});
socket.on('system',d=>{let sys=document.createElement('div');sys.className='system-msg';sys.textContent=d.text;msgDiv.appendChild(sys);msgDiv.scrollTop=msgDiv.scrollHeight;});
socket.on('friend_request',data=>{addNotification('Заявка',`${data.from} хочет добавить вас`);loadRequests();});
socket.on('rooms',l=>{
    let c=document.getElementById('roomsList');
    c.innerHTML=l.map(r=>`<div class="room-item ${r===currentRoom?'active':''}" data-room="${r}">🏠 ${escape(r)}${role==='owner'||role==='admin'?`<button class="delete-room" onclick="event.stopPropagation();deleteRoom('${escape(r)}')">🗑</button>`:''}</div>`).join('');
    document.querySelectorAll('.room-item').forEach(el=>{el.onclick=()=>{
        let nr=el.dataset.room;
        if(nr===currentRoom)return;
        socket.emit('switch',{old:currentRoom,new:nr});
        currentRoom=nr;
        document.getElementById('roomName').innerText=currentRoom;
        document.querySelectorAll('.room-item').forEach(i=>i.classList.remove('active'));
        el.classList.add('active');
        showSkeleton();
        msgDiv.innerHTML='';
        setTimeout(()=>{hideSkeleton();},500);
        if(window.innerWidth<=680) sidebar.classList.remove('open'),overlay.style.display='none';
    };});
});
socket.on('users',l=>{
    let c=document.getElementById('usersList');
    c.innerHTML=l.map(u=>`<div class="user-item" onclick="showUserProfile('${escape(u.name)}')"><span class="online-dot"></span> ${u.avatar_base64?`<img src="${u.avatar_base64}" style="width:24px;height:24px;border-radius:50%;object-fit:cover;">`:u.avatar||'👤'} ${escape(u.name)} ${u.role==='owner'?'<span class="badge-owner">ВЛ</span>':(u.role==='admin'?'<span class="badge-admin">АДМ</span>':(u.role==='moderator'?'<span class="badge-moderator">МОД</span>':''))}</div>`).join('');
    loadDMList();
    updateAllUsersCount();
});
socket.on('friends',l=>{let c=document.getElementById('friendsList');if(c)c.innerHTML=l.map(f=>`<div class="user-item" onclick="showUserProfile('${escape(f.name)}')">👫 ${escape(f.name)}</div>`).join('');});
socket.on('typing',d=>{if(d.typing)typingUsers[d.name]=true;else delete typingUsers[d.name];let n=Object.keys(typingUsers).filter(n=>n!==username);document.getElementById('typingStatus').innerText=n.length?(n.length===1?`${n[0]} печатает...`:`${n.length} человек печатают...`):'';});
socket.on('update_online_users',()=>{});
document.getElementById('sendBtn').onclick=()=>{let t=msgInput.value.trim();if(t){socket.emit('message',{text:t,room:currentRoom});msgInput.value='';}};
msgInput.onkeypress=e=>{if(e.key==='Enter')document.getElementById('sendBtn').click();socket.emit('typing',{room:currentRoom,typing:true});clearTimeout(window.tt);window.tt=setTimeout(()=>socket.emit('typing',{room:currentRoom,typing:false}),1000);};
document.getElementById('createRoomBtn')?.addEventListener('click',()=>{let n=document.getElementById('newRoom').value.trim();if(n){socket.emit('create',{room:n});document.getElementById('newRoom').value='';}});
function deleteRoom(roomName){
    if(roomName==='Главная'){showToast('Нельзя удалить главную комнату','error');return;}
    if(confirm(`Удалить комнату "${roomName}"?`)){
        fetch('/delete_room',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({room:roomName})}).then(r=>r.json()).then(data=>{
            let sys=document.createElement('div');sys.className='system-msg';sys.textContent=data.message;msgDiv.appendChild(sys);msgDiv.scrollTop=msgDiv.scrollHeight;
            if(data.success && currentRoom===roomName){
                socket.emit('switch',{old:currentRoom,new:'Главная'});
                currentRoom='Главная';
                document.getElementById('roomName').innerText='Главная';
                showSkeleton();
                setTimeout(()=>{hideSkeleton();},500);
            }
            showToast(data.message,data.success?'success':'error');
        });
    }
}
document.getElementById('profileBtn').onclick=()=>document.getElementById('profileModal').style.display='flex';
document.getElementById('settingsBtn').onclick=()=>document.getElementById('settingsModal').style.display='flex';
document.getElementById('closeProfile').onclick=()=>document.getElementById('profileModal').style.display='none';
document.getElementById('closeSettings').onclick=()=>document.getElementById('settingsModal').style.display='none';
document.getElementById('closeUserModal').onclick=()=>document.getElementById('userModal').style.display='none';
document.getElementById('saveProfile').onclick=()=>{
    fetch('/update_profile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
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
window.onclick=e=>{
    if(e.target===document.getElementById('profileModal'))document.getElementById('profileModal').style.display='none';
    if(e.target===document.getElementById('settingsModal'))document.getElementById('settingsModal').style.display='none';
    if(e.target===document.getElementById('notifyModal'))document.getElementById('notifyModal').style.display='none';
    if(e.target===document.getElementById('userModal'))document.getElementById('userModal').style.display='none';
    if(e.target===document.getElementById('reportsModal'))document.getElementById('reportsModal').style.display='none';
    if(e.target===document.getElementById('previewModal'))document.getElementById('previewModal').style.display='none';
    if(e.target===document.getElementById('fullscreenDm'))document.getElementById('fullscreenDm').style.display='none';
    if(e.target===overlay){sidebar.classList.remove('open');overlay.style.display='none';}
};
loadRequests();socket.emit('get_rooms');socket.emit('get_users');
</script>
</body>
</html>
'''

# -------------------------- МАРШРУТЫ (без изменений) --------------------------
@app.route('/')
def index():
    if 'username' not in session: return redirect(url_for('login'))
    u = users.get(session['username'])
    if not u or u.get('banned'): session.clear(); return redirect(url_for('login'))
    return render_template_string(CHAT_HTML, username=session['username'], role=u['role'], avatar_base64=u.get('avatar_base64'), bio=u.get('bio',''), user_id=u.get('user_id',''))

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
        if len(name)<3 or len(name)>20: return render_template_string(REGISTER_HTML, error='Имя 3-20')
        if len(pwd)<4: return render_template_string(REGISTER_HTML, error='Пароль мин 4')
        users[name] = {'password': hashlib.sha256(pwd.encode()).hexdigest(), 'role': 'user', 'avatar_base64': None, 'bio': '', 'friends': [], 'requests': [], 'banned': False, 'theme': 'light', 'user_id': short_id(), 'id_change_count': 0, 'last_id_change': None, 'muted_until': None}
        save_json(USERS_FILE, users); return redirect(url_for('login'))
    return render_template_string(REGISTER_HTML)

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/save_theme', methods=['POST'])
def save_theme():
    if 'username' in session: users[session['username']]['theme'] = request.json.get('theme', 'light'); save_json(USERS_FILE, users)
    return jsonify({'success': True})

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'username' not in session: return jsonify({'error': 'Not logged'}), 401
    name = session['username']; data = request.json
    if data.get('avatar_base64'): users[name]['avatar_base64'] = data['avatar_base64']
    if data.get('bio') is not None: users[name]['bio'] = data['bio'][:200]
    if data.get('new_name'):
        nn = data['new_name']
        if len(nn)<3 or len(nn)>20: return jsonify({'error': 'Имя 3-20'}), 400
        if nn in users and nn != name: return jsonify({'error': 'Имя занято'}), 400
        users[nn] = users.pop(name); session['username'] = nn
    if data.get('new_password') and len(data['new_password'])>=4: users[session['username']]['password'] = hashlib.sha256(data['new_password'].encode()).hexdigest()
    save_json(USERS_FILE, users); return jsonify({'success': True})

@app.route('/change_id', methods=['POST'])
def change_id():
    if 'username' not in session: return jsonify({'error': 'Not logged'}), 401
    name = session['username']; new_id = request.json.get('new_id')
    if not new_id or not new_id.isdigit() or len(new_id)<4 or len(new_id)>8: return jsonify({'error': 'ID должен быть числом от 4 до 8 цифр'})
    u = users[name]
    if u['id_change_count'] == 0:
        u['user_id'] = new_id; u['id_change_count'] = 1; u['last_id_change'] = datetime.now().isoformat(); save_json(USERS_FILE, users); return jsonify({'success': True})
    else:
        last = datetime.fromisoformat(u['last_id_change']) if u['last_id_change'] else None
        if last and datetime.now() - last < timedelta(days=14):
            nxt = last + timedelta(days=14)
            return jsonify({'error': f'Следующая смена ID с {nxt.strftime("%d.%m.%Y %H:%M")}'})
        u['user_id'] = new_id; u['last_id_change'] = datetime.now().isoformat(); save_json(USERS_FILE, users); return jsonify({'success': True})

@app.route('/id_change_info')
def id_change_info():
    if 'username' not in session: return jsonify({'can_change': False, 'next_change_date': ''})
    u = users[session['username']]
    if u['id_change_count'] == 0: return jsonify({'can_change': True, 'next_change_date': ''})
    last = datetime.fromisoformat(u['last_id_change']) if u['last_id_change'] else None
    if last and datetime.now() - last < timedelta(days=14):
        nxt = last + timedelta(days=14)
        return jsonify({'can_change': False, 'next_change_date': nxt.strftime("%d.%m.%Y %H:%M")})
    return jsonify({'can_change': True, 'next_change_date': ''})

@app.route('/delete_room', methods=['POST'])
def delete_room():
    if 'username' not in session or users[session['username']]['role'] not in ['owner','admin']:
        return jsonify({'success': False, 'message': 'Нет прав'})
    room = request.json.get('room')
    if room == 'Главная': return jsonify({'success': False, 'message': 'Нельзя удалить главную комнату'})
    if room in rooms:
        rooms.remove(room)
        if room in messages: del messages[room]
        save_json(ROOMS_FILE, rooms); save_json(MESSAGES_FILE, messages)
        socketio.emit('rooms', rooms, broadcast=True)
        return jsonify({'success': True, 'message': f'Комната "{room}" удалена'})
    return jsonify({'success': False, 'message': 'Комната не найдена'})

@app.route('/give_role', methods=['POST'])
def give_role():
    if 'username' not in session or users[session['username']]['role'] not in ['owner','admin']:
        return jsonify({'success': False, 'message': 'Нет прав'})
    target = request.json.get('username'); new_role = request.json.get('role')
    if target not in users: return jsonify({'success': False, 'message': 'Пользователь не найден'})
    if users[target]['role'] == 'owner': return jsonify({'success': False, 'message': 'Нельзя изменить роль владельца'})
    users[target]['role'] = new_role
    save_json(USERS_FILE, users)
    socketio.emit('system', {'text': f'⭐ {target} назначен {role_display(new_role)}'}, broadcast=True)
    return jsonify({'success': True, 'message': f'Роль {target} изменена на {role_display(new_role)}'})

@app.route('/remove_role', methods=['POST'])
def remove_role():
    if 'username' not in session or users[session['username']]['role'] not in ['owner','admin']:
        return jsonify({'success': False, 'message': 'Нет прав'})
    target = request.json.get('username'); old_role = request.json.get('role')
    if target not in users: return jsonify({'success': False, 'message': 'Пользователь не найден'})
    if users[target]['role'] == 'owner': return jsonify({'success': False, 'message': 'Нельзя снять роль владельца'})
    if users[target]['role'] == old_role:
        users[target]['role'] = 'user'
        save_json(USERS_FILE, users)
        socketio.emit('system', {'text': f'🔻 У {target} снята роль {role_display(old_role)}'}, broadcast=True)
        return jsonify({'success': True, 'message': f'У {target} снята привилегия'})
    return jsonify({'success': False, 'message': 'Роль не соответствует'})

@app.route('/report_user', methods=['POST'])
def report_user():
    if 'username' not in session: return jsonify({'success': False, 'message': 'Войдите'})
    from_user = session['username']
    data = request.json
    target = data.get('target'); reason = data.get('reason')
    if target not in users: return jsonify({'success': False, 'message': 'Пользователь не найден'})
    report = {'id': len(reports)+1, 'from': from_user, 'target': target, 'reason': reason, 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'resolved': False}
    reports.append(report); save_json(REPORTS_FILE, reports)
    return jsonify({'success': True, 'message': 'Жалоба отправлена администрации'})

@app.route('/get_reports')
def get_reports():
    if 'username' not in session or users[session['username']]['role'] not in ['owner','admin']: return jsonify({'reports': []})
    active = [r for r in reports if not r.get('resolved')]
    return jsonify({'reports': active})

@app.route('/resolve_report', methods=['POST'])
def resolve_report():
    if 'username' not in session or users[session['username']]['role'] not in ['owner','admin']: return jsonify({'message': 'Нет прав'})
    rid = request.json.get('id')
    for r in reports:
        if r['id'] == rid:
            r['resolved'] = True
            save_json(REPORTS_FILE, reports)
            return jsonify({'message': 'Жалоба помечена как решённая'})
    return jsonify({'message': 'Жалоба не найдена'})

@app.route('/registered_users_count')
def registered_users_count():
    return jsonify({'count': len([u for u in users if not users[u].get('banned')])})

@app.route('/get_notifications')
def get_notifications():
    if 'username' not in session: return jsonify([])
    return jsonify(load_user_notifs(session['username']))

@app.route('/add_notification', methods=['POST'])
def add_notification():
    if 'username' not in session: return jsonify({'status': 'error'})
    data = request.json
    notif = {'title': data.get('title'), 'text': data.get('text'), 'time': datetime.now().strftime('%H:%M:%S')}
    notifs = load_user_notifs(session['username'])
    notifs.insert(0, notif)
    save_user_notifs(session['username'], notifs)
    return jsonify({'status': 'ok'})

@app.route('/give_admin', methods=['POST'])
def give_admin():
    if 'username' not in session or users[session['username']]['role']!='owner': return jsonify({'message': 'Только владелец'})
    target = request.json.get('username')
    if target in users and users[target]['role'] not in ['owner','admin']:
        users[target]['role'] = 'admin'; save_json(USERS_FILE, users); socketio.emit('system',{'text':f'⭐ {target} назначен администратором!'}, broadcast=True); return jsonify({'message': f'{target} теперь админ'})
    return jsonify({'message': 'Не найден или уже админ'})

@app.route('/remove_admin', methods=['POST'])
def remove_admin():
    if 'username' not in session or users[session['username']]['role']!='owner': return jsonify({'message': 'Только владелец'})
    target = request.json.get('username')
    if target in users and users[target]['role'] == 'admin':
        users[target]['role'] = 'user'; save_json(USERS_FILE, users); socketio.emit('system',{'text':f'🔻 У {target} снята админка'}, broadcast=True); return jsonify({'message': f'У {target} снята админка'})
    return jsonify({'message': 'Не найден или не админ'})

@app.route('/mute_user', methods=['POST'])
def mute_user():
    if 'username' not in session or users[session['username']]['role'] not in ['owner','admin']: return jsonify({'message': 'Нет прав'})
    target = request.json.get('username'); minutes = int(request.json.get('minutes',5))
    if target not in users or users[target]['role']=='owner': return jsonify({'message': 'Нельзя замутить владельца'})
    users[target]['muted_until'] = (datetime.now()+timedelta(minutes=minutes)).isoformat(); save_json(USERS_FILE, users)
    socketio.emit('system',{'text':f'🔇 {target} замучен на {minutes} минут'}, broadcast=True)
    return jsonify({'message': f'{target} замучен на {minutes} минут'})

@app.route('/unmute_user', methods=['POST'])
def unmute_user():
    if 'username' not in session or users[session['username']]['role'] not in ['owner','admin']: return jsonify({'message': 'Нет прав'})
    target = request.json.get('username')
    if target not in users: return jsonify({'message': 'Не найден'})
    users[target]['muted_until'] = None; save_json(USERS_FILE, users)
    socketio.emit('system',{'text':f'🔊 {target} размучен!'}, broadcast=True)
    return jsonify({'message': f'{target} размучен'})

@app.route('/ban_user', methods=['POST'])
def ban_user():
    if 'username' not in session or users[session['username']]['role'] not in ['owner','admin']: return jsonify({'message': 'Нет прав'})
    target = request.json.get('username')
    if target not in users or users[target]['role']=='owner': return jsonify({'message': 'Нельзя забанить владельца'})
    users[target]['banned'] = True; save_json(USERS_FILE, users)
    socketio.emit('system',{'text':f'🔨 {target} забанен!'}, broadcast=True)
    return jsonify({'message': f'{target} забанен'})

@app.route('/unban_user', methods=['POST'])
def unban_user():
    if 'username' not in session or users[session['username']]['role'] not in ['owner','admin']: return jsonify({'message': 'Нет прав'})
    target = request.json.get('username')
    if target in users:
        users[target]['banned'] = False; save_json(USERS_FILE, users)
        socketio.emit('system',{'text':f'🔓 {target} разбанен!'}, broadcast=True)
        return jsonify({'message': f'{target} разбанен'})
    return jsonify({'message': 'Не найден'})

@app.route('/add_friend', methods=['POST'])
def add_friend():
    if 'username' not in session: return jsonify({'message': 'Войдите'})
    name = session['username']; target = request.json.get('friend')
    if target not in users: return jsonify({'message': 'Не найден'})
    if target==name: return jsonify({'message': 'Себя нельзя'})
    if target in users[name]['friends']: return jsonify({'message': 'Уже друг'})
    if target in users[name]['requests']: return jsonify({'message': 'Заявка уже отправлена'})
    users[target]['requests'].append(name); save_json(USERS_FILE, users); socketio.emit('friend_request',{'from':name}, to=target)
    return jsonify({'message': f'Заявка отправлена {target}'})

@app.route('/accept_friend', methods=['POST'])
def accept_friend():
    if 'username' not in session: return jsonify({'message': 'Войдите'})
    name = session['username']; target = request.json.get('friend')
    if target not in users[name]['requests']: return jsonify({'message': 'Нет заявки'})
    users[name]['requests'].remove(target); users[name]['friends'].append(target); users[target]['friends'].append(name); save_json(USERS_FILE, users)
    return jsonify({'message': f'Вы приняли заявку от {target}'})

@app.route('/remove_friend', methods=['POST'])
def remove_friend():
    if 'username' not in session: return jsonify({'message': 'Войдите'})
    name = session['username']; target = request.json.get('friend')
    if target in users[name]['friends']:
        users[name]['friends'].remove(target); users[target]['friends'].remove(name); save_json(USERS_FILE, users); return jsonify({'message': f'{target} удалён из друзей'})
    return jsonify({'message': 'Не в друзьях'})

@app.route('/get_requests')
def get_requests():
    if 'username' not in session: return jsonify({'requests': []})
    return jsonify({'requests': users[session['username']].get('requests', [])})

@app.route('/user_info/<name>')
def user_info(name):
    if name not in users: return jsonify({'error': 'Not found'}), 404
    u = users[name]
    is_friend = name in users.get(session.get('username',''),{}).get('friends',[]) if session.get('username') else False
    role_display = role_display(u['role'])
    return jsonify({'username':name,'bio':u.get('bio',''),'role_display':role_display,'user_role':u['role'],'avatar_base64':u.get('avatar_base64'),'user_id':u.get('user_id',''),'friends_count':len(u.get('friends',[])),'is_friend':is_friend,'banned':u.get('banned',False),'muted':u.get('muted_until') and datetime.now()<datetime.fromisoformat(u['muted_until'])})

@app.route('/get_dm_list')
def get_dm_list():
    if 'username' not in session: return jsonify({'dms': []})
    name = session['username']; result = []
    for key, conv in dms.items():
        parts = key.split('_')
        if name in parts:
            other = parts[0] if parts[1]==name else parts[1]
            last = conv[-1] if conv else None
            result.append({'with': other, 'last_preview': last['text'][:30] if last else ''})
    return jsonify({'dms': result})

@app.route('/get_dm/<target>')
def get_dm(target):
    if 'username' not in session: return jsonify({'messages': []})
    name = session['username']; key = f"{min(name,target)}_{max(name,target)}"
    return jsonify({'messages': dms.get(key, [])})

# -------------------------- SOCKET.IO --------------------------
@socketio.on('connect')
def handle_connect():
    if 'username' in session:
        online_users.add(session['username'])

@socketio.on('disconnect')
def handle_disconnect():
    if 'username' in session:
        online_users.discard(session['username'])

@socketio.on('private_message')
def private_message(data):
    username = session.get('username')
    if not username: return
    target = data['target']; text = data['text']
    key = f"{min(username,target)}_{max(username,target)}"
    msg = {'from': username, 'to': target, 'text': text, 'time': datetime.now().strftime('%H:%M')}
    dms.setdefault(key, []).append(msg); save_json(DMS_FILE, dms)
    emit('private_message', msg, to=target); emit('private_message', msg, to=username)

@socketio.on('voice_message')
def voice_message(data):
    username = session.get('username')
    if not username or users.get(username,{}).get('banned'): return
    room = data['room']; audio = data['data']
    mid = str(int(datetime.now().timestamp()*1000))
    msg = {'id': mid, 'name': username, 'voice': audio, 'time': datetime.now().strftime('%H:%M'), 'avatar': users[username].get('avatar','👤'), 'avatar_base64': users[username].get('avatar_base64')}
    messages.setdefault(room, []).append(msg)
    if len(messages[room])>100: messages[room] = messages[room][-100:]
    save_json(MESSAGES_FILE, messages)
    emit('voice_message', msg, to=room, broadcast=True)

@socketio.on('delete_message')
def delete_message(data):
    username = session.get('username')
    if not username: return
    room = data['room']; mid = data['messageId']
    for i, m in enumerate(messages.get(room, [])):
        if str(m.get('id')) == mid and (m['name'] == username or users[username]['role'] in ['owner','admin']):
            messages[room].pop(i)
            save_json(MESSAGES_FILE, messages)
            emit('delete_message', {'messageId': mid}, to=room, broadcast=True)
            break

@socketio.on('file_message')
def file_message(data):
    username = session.get('username')
    if not username or users.get(username,{}).get('banned'): return
    room = data['room']; name = data['name']; filedata = data['data']; ftype = data['type']; is_img = data['isImage']
    mid = str(int(datetime.now().timestamp()*1000))
    msg = {'id': mid, 'name': username, 'text': '', 'time': datetime.now().strftime('%H:%M'), 'avatar': users[username].get('avatar','👤'), 'avatar_base64': users[username].get('avatar_base64'), 'file': {'name': name, 'data': filedata, 'type': ftype, 'isImage': is_img}}
    messages.setdefault(room, []).append(msg)
    if len(messages[room])>100: messages[room] = messages[room][-100:]
    save_json(MESSAGES_FILE, messages)
    emit('file_message', msg, to=room, broadcast=True)

@socketio.on('join')
def on_join(data):
    username = session.get('username')
    if not username or users.get(username,{}).get('banned'): return
    room = data['room']; join_room(room); emit('history', messages.get(room, []), to=request.sid)

@socketio.on('message')
def on_message(data):
    username = session.get('username')
    if not username or users.get(username,{}).get('banned'): return
    u = users.get(username)
    if u.get('muted_until') and datetime.now() < datetime.fromisoformat(u['muted_until']):
        emit('system', {'text': '🔇 Вы замучены и не можете писать!'}, to=request.sid); return
    room = data['room']; text = data['text']
    mid = str(int(datetime.now().timestamp()*1000))
    msg = {'id': mid, 'name': username, 'text': text, 'time': datetime.now().strftime('%H:%M'), 'avatar': users[username].get('avatar','👤'), 'avatar_base64': users[username].get('avatar_base64')}
    messages.setdefault(room, []).append(msg)
    if len(messages[room])>100: messages[room] = messages[room][-100:]
    save_json(MESSAGES_FILE, messages)
    emit('message', msg, to=room, broadcast=True)

@socketio.on('switch')
def on_switch(data):
    username = session.get('username')
    if not username: return
    old = data['old']; new = data['new']; leave_room(old); join_room(new); emit('history', messages.get(new, []), to=request.sid)

@socketio.on('create')
def on_create(data):
    username = session.get('username')
    if not username or users[username]['role'] not in ['owner','admin']: return
    new_room = data['room'].strip()
    if new_room and new_room not in rooms:
        rooms.append(new_room); messages[new_room] = []; save_json(ROOMS_FILE, rooms); save_json(MESSAGES_FILE, messages); emit('rooms', rooms, broadcast=True)

@socketio.on('typing')
def on_typing(data):
    username = session.get('username')
    if not username: return
    emit('typing', {'name': username, 'typing': data['typing']}, to=data['room'], broadcast=True, include_self=False)

@socketio.on('get_rooms')
def get_rooms(): emit('rooms', rooms)

@socketio.on('get_users')
def get_users():
    lst = [{'name': n, 'role': u['role'], 'avatar': '👤', 'avatar_base64': u.get('avatar_base64')} for n, u in users.items() if not u.get('banned')]
    emit('users', lst, broadcast=True)
    if session.get('username'):
        name = session['username']; friends = [{'name': f} for f in users[name].get('friends',[])]; emit('friends', friends, to=request.sid)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
