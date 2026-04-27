from flask import Flask, render_template_string, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import os
import json
import hashlib
import base64

app = Flask(__name__)
app.secret_key = 'chatic-secret-key-2024'
socketio = SocketIO(app, cors_allowed_origins="*")

# Файлы данных
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
            'bio': 'Владелец чата 👑',
            'friends': [],
            'friend_requests': [],
            'banned': False,
            'theme': 'light'
        },
        'dimooon': {
            'password': hashlib.sha256('1111'.encode()).hexdigest(),
            'role': 'admin',
            'avatar': '😎',
            'avatar_base64': None,
            'bio': 'Администратор ⚙️',
            'friends': [],
            'friend_requests': [],
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

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def get_user():
    username = session.get('username')
    if not username or username not in users or users[username].get('banned'):
        return None, None
    return username, users[username]

# ========== МАРШРУТЫ ==========
@app.route('/')
def index():
    username, user = get_user()
    if not username:
        return redirect(url_for('login'))
    role_names = {'owner': 'Владелец', 'admin': 'Админ', 'moderator': 'Модератор', 'user': 'Пользователь'}
    return render_template_string(CHAT_TEMPLATE, 
        username=username, role=user['role'], 
        role_name=role_names.get(user['role'], 'Пользователь'),
        avatar=user.get('avatar', '👤'),
        avatar_base64=user.get('avatar_base64'),
        bio=user.get('bio', ''),
        user_theme=user.get('theme', 'light')
    )

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
            return render_template_string(REGISTER_TEMPLATE, error='Имя от 3 до 20 символов')
        if len(password) < 4:
            return render_template_string(REGISTER_TEMPLATE, error='Пароль минимум 4 символа')
        users[username] = {
            'password': hashlib.sha256(password.encode()).hexdigest(),
            'role': 'user',
            'avatar': '👤',
            'avatar_base64': None,
            'bio': '',
            'friends': [],
            'friend_requests': [],
            'banned': False,
            'theme': 'light'
        }
        save_users(users)
        return redirect(url_for('login'))
    return render_template_string(REGISTER_TEMPLATE, error=None)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/save_theme', methods=['POST'])
def save_theme():
    username, user = get_user()
    if not username:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.json
    users[username]['theme'] = data.get('theme', 'light')
    save_users(users)
    return jsonify({'success': True})

@app.route('/update_profile', methods=['POST'])
def update_profile():
    username, user = get_user()
    if not username:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.json
    if data.get('avatar_emoji'):
        users[username]['avatar'] = data['avatar_emoji'][:2]
    if data.get('avatar_base64'):
        users[username]['avatar_base64'] = data['avatar_base64']
    if data.get('bio') is not None:
        users[username]['bio'] = data['bio'][:200]
    if data.get('new_name'):
        new_name = data['new_name']
        if len(new_name) < 3 or len(new_name) > 20:
            return jsonify({'error': 'Имя от 3 до 20 символов'}), 400
        if new_name in users and new_name != username:
            return jsonify({'error': 'Имя уже занято'}), 400
        users[new_name] = users.pop(username)
        session['username'] = new_name
        username = new_name
    if data.get('new_password') and len(data['new_password']) >= 4:
        users[username]['password'] = hashlib.sha256(data['new_password'].encode()).hexdigest()
    save_users(users)
    return jsonify({'success': True})

@app.route('/give_admin', methods=['POST'])
def give_admin():
    username, user = get_user()
    if not username or user['role'] != 'owner':
        return jsonify({'message': 'Только владелец может выдавать админку'})
    target = request.json.get('username')
    if target in users and users[target]['role'] != 'owner':
        users[target]['role'] = 'admin'
        save_users(users)
        socketio.emit('system_message', {'text': f'⭐ {target} назначен администратором!'}, broadcast=True)
        return jsonify({'message': f'{target} теперь администратор'})
    return jsonify({'message': 'Пользователь не найден'})

@app.route('/remove_admin', methods=['POST'])
def remove_admin():
    username, user = get_user()
    if not username or user['role'] != 'owner':
        return jsonify({'message': 'Только владелец может снимать админку'})
    target = request.json.get('username')
    if target in users and users[target]['role'] == 'admin':
        users[target]['role'] = 'user'
        save_users(users)
        return jsonify({'message': f'У {target} снята роль администратора'})
    return jsonify({'message': 'Пользователь не найден или не является админом'})

@app.route('/add_friend', methods=['POST'])
def add_friend():
    username, user = get_user()
    if not username:
        return jsonify({'message': 'Не авторизован'}), 401
    target = request.json.get('friend')
    if target not in users:
        return jsonify({'message': 'Пользователь не найден'})
    if target == username:
        return jsonify({'message': 'Нельзя добавить себя'})
    if target in user['friends']:
        return jsonify({'message': 'Уже в друзьях'})
    if target in user['friend_requests']:
        return jsonify({'message': 'Заявка уже отправлена'})
    users[target]['friend_requests'].append(username)
    save_users(users)
    return jsonify({'message': f'Заявка отправлена {target}'})

@app.route('/accept_friend', methods=['POST'])
def accept_friend():
    username, user = get_user()
    if not username:
        return jsonify({'message': 'Не авторизован'}), 401
    target = request.json.get('friend')
    if target not in user['friend_requests']:
        return jsonify({'message': 'Нет заявки от этого пользователя'})
    user['friend_requests'].remove(target)
    user['friends'].append(target)
    users[target]['friends'].append(username)
    save_users(users)
    return jsonify({'message': f'Вы приняли заявку от {target}'})

@app.route('/get_friend_requests')
def get_friend_requests():
    username, user = get_user()
    if not username:
        return jsonify({'requests': []})
    return jsonify({'requests': user.get('friend_requests', [])})

@app.route('/get_user_info/<name>')
def get_user_info(name):
    if name not in users:
        return jsonify({'error': 'Not found'}), 404
    u = users[name]
    role_display = {'owner': 'Владелец', 'admin': 'Админ', 'moderator': 'Модератор', 'user': 'Пользователь'}.get(u.get('role'), 'Пользователь')
    return jsonify({
        'username': name,
        'bio': u.get('bio', ''),
        'role_display': role_display,
        'friends_count': len(u.get('friends', []))
    })

# ========== ШАБЛОНЫ ==========
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Чатик - Вход</title><style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center}.card{background:white;border-radius:48px;padding:48px;max-width:400px;width:100%;text-align:center}h1{margin-bottom:8px;background:linear-gradient(135deg,#667eea,#764ba2);-webkit-background-clip:text;-webkit-text-fill-color:transparent}.subtitle{color:#6b7280;margin-bottom:32px}input{width:100%;padding:16px;border:2px solid #e5e7eb;border-radius:32px;margin-bottom:16px}button{width:100%;padding:16px;background:#667eea;color:white;border:none;border-radius:32px;cursor:pointer}.error{background:#fee2e2;color:#dc2626;padding:12px;border-radius:24px;margin-bottom:20px}.footer{margin-top:24px}a{color:#667eea}
</style></head>
<body><div class="card"><h1>💬 Чатик</h1><div class="subtitle">Общайся с друзьями</div>{% if error %}<div class="error">{{ error }}</div>{% endif %}<form method="post"><input type="text" name="username" placeholder="Имя" required autofocus><input type="password" name="password" placeholder="Пароль" required><button type="submit">Войти</button></form><div class="footer">Нет аккаунта? <a href="/register">Регистрация</a></div></div></body>
</html>
'''

REGISTER_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Чатик - Регистрация</title><style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center}.card{background:white;border-radius:48px;padding:48px;max-width:400px;width:100%}h1{text-align:center;margin-bottom:32px;background:linear-gradient(135deg,#667eea,#764ba2);-webkit-background-clip:text;-webkit-text-fill-color:transparent}input{width:100%;padding:16px;border:2px solid #e5e7eb;border-radius:32px;margin-bottom:16px}button{width:100%;padding:16px;background:#667eea;color:white;border:none;border-radius:32px;cursor:pointer}.error{background:#fee2e2;color:#dc2626;padding:12px;border-radius:24px;margin-bottom:20px}.footer{text-align:center;margin-top:24px}a{color:#667eea}
</style></head>
<body><div class="card"><h1>📝 Регистрация</h1>{% if error %}<div class="error">{{ error }}</div>{% endif %}<form method="post"><input type="text" name="username" placeholder="Имя (3-20 символов)" required autofocus><input type="password" name="password" placeholder="Пароль (мин. 4)" required><button type="submit">Создать аккаунт</button></form><div class="footer">Уже есть аккаунт? <a href="/login">Войти</a></div></div></body>
</html>
'''

CHAT_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Чатик · {{ username }}</title>
<script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);height:100vh;display:flex;transition:0.3s}body.dark{background:#1e1b4b}.sidebar{width:280px;background:rgba(255,255,255,0.95);backdrop-filter:blur(10px);border-right:1px solid rgba(0,0,0,0.1);display:flex;flex-direction:column;padding:20px;overflow-y:auto}body.dark .sidebar{background:#1f2937;color:#fff}.user-card{text-align:center;padding:20px;background:linear-gradient(135deg,#667eea,#764ba2);border-radius:24px;color:#fff;margin-bottom:20px;cursor:pointer}.user-avatar{width:64px;height:64px;border-radius:50%;background:rgba(255,255,255,0.2);display:flex;align-items:center;justify-content:center;margin:0 auto 10px;font-size:32px;overflow:hidden}.user-avatar img{width:100%;height:100%;object-fit:cover}.section-title{font-weight:600;margin:16px 0 8px 0;color:#374151}body.dark .section-title{color:#9ca3af}.room-item,.user-item{padding:10px 12px;border-radius:12px;cursor:pointer;margin-bottom:4px;display:flex;align-items:center;gap:8px}.room-item:hover,.user-item:hover{background:rgba(0,0,0,0.05)}.room-item.active{background:#667eea;color:#fff}.add-room{display:flex;gap:8px;margin-top:12px}.add-room input{flex:1;padding:8px 12px;border:1px solid #ddd;border-radius:20px;outline:none}.add-room button{background:#667eea;color:#fff;border:none;border-radius:20px;padding:8px 16px;cursor:pointer}.chat-area{flex:1;display:flex;flex-direction:column;background:#fff;transition:0.3s}body.dark .chat-area{background:#111827}.chat-header{padding:16px 24px;border-bottom:1px solid #eee;background:#fff;display:flex;justify-content:space-between}body.dark .chat-header{background:#1f2937;color:#fff;border-color:#374151}.messages{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:12px}.message{display:flex;gap:10px;align-items:flex-start}.message-own{justify-content:flex-end}.message-avatar{width:32px;height:32px;border-radius:50%;background:#667eea;display:flex;align-items:center;justify-content:center;font-size:14px;color:#fff;overflow:hidden}.message-content{background:#f3f4f6;padding:8px 14px;border-radius:18px;max-width:60%}body.dark .message-content{background:#374151;color:#fff}.message-own .message-content{background:#667eea;color:#fff}.message-name{font-size:12px;font-weight:700;margin-bottom:4px}.message-time{font-size:10px;opacity:0.6;margin-left:8px}.system-msg{text-align:center;font-size:12px;color:#6b7280;padding:4px}.typing{padding:8px 24px;font-size:12px;color:#6b7280;font-style:italic}.input-area{display:flex;gap:12px;padding:16px 24px;border-top:1px solid #eee;background:#fff}body.dark .input-area{background:#1f2937;border-color:#374151}.input-area input{flex:1;padding:12px 18px;border:1px solid #ddd;border-radius:30px;outline:none}body.dark .input-area input{background:#374151;color:#fff;border-color:#4b5563}.input-area button{background:#667eea;border:none;border-radius:50%;width:46px;height:46px;color:#fff;cursor:pointer}.btn-settings,.btn-logout{margin-top:10px;padding:10px;border:none;border-radius:20px;cursor:pointer;width:100%}.btn-settings{background:#e0e7ff;color:#4f46e5}.btn-logout{background:#fee2e2;color:#dc2626}body.dark .btn-settings{background:#374151;color:#818cf8}body.dark .btn-logout{background:#374151;color:#f87171}.badge-owner{background:#ef4444;font-size:9px;padding:2px 6px;border-radius:12px;margin-left:6px}.badge-admin{background:#10b981;font-size:9px;padding:2px 6px;border-radius:12px;margin-left:6px}.online-dot{width:8px;height:8px;background:#10b981;border-radius:50%;display:inline-block;margin-right:6px}.modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);align-items:center;justify-content:center;z-index:1000}.modal-content{background:#fff;border-radius:32px;padding:32px;max-width:400px;width:90%;max-height:80vh;overflow-y:auto}body.dark .modal-content{background:#1f2937;color:#fff}.modal-content input,.modal-content textarea{width:100%;padding:12px;margin:10px 0;border:1px solid #ddd;border-radius:24px}.modal-content button{background:#667eea;color:#fff;border:none;padding:12px;border-radius:24px;width:100%;cursor:pointer;margin-top:10px}.close-btn{float:right;font-size:24px;cursor:pointer}@media(max-width:600px){.sidebar{width:220px}}
</style>
</head>
<body>
<div class="sidebar">
    <div class="user-card" id="profileBtn">
        <div class="user-avatar">{% if avatar_base64 %}<img src="{{ avatar_base64 }}">{% else %}{{ avatar }}{% endif %}</div>
        <div><strong>{{ username }}</strong>{% if role == 'owner' %}<span class="badge-owner">ВЛ</span>{% elif role == 'admin' %}<span class="badge-admin">АДМ</span>{% endif %}</div>
        <div style="font-size:11px;">{{ bio[:50] }}</div>
        <div style="font-size:10px;">{{ role_name }}</div>
    </div>
    <div class="section-title">📌 Комнаты</div>
    <div id="roomsList"></div>
    {% if role in ['owner', 'admin'] %}
    <div class="add-room"><input type="text" id="newRoomName" placeholder="Название"><button id="createRoomBtn">+</button></div>
    {% endif %}
    <div class="section-title">👥 В чате</div>
    <div id="usersList"></div>
    <div class="section-title">👫 Друзья</div>
    <div id="friendsList"></div>
    <button class="btn-settings" id="settingsBtn">⚙️ Настройки</button>
    <button class="btn-logout" id="logoutBtn">🚪 Выйти</button>
</div>
<div class="chat-area">
    <div class="chat-header"><span id="currentRoomSpan">Главная</span><span id="onlineCount">👥 0</span></div>
    <div id="messagesList" class="messages"></div>
    <div id="typingStatus" class="typing"></div>
    <div class="input-area"><input type="text" id="messageInput" placeholder="Сообщение..."><button id="sendBtn">📤</button></div>
</div>

<div id="profileModal" class="modal"><div class="modal-content">
    <span class="close-btn" id="closeProfileModal">&times;</span>
    <h3>👤 Мой профиль</h3>
    <label>Аватар (эмодзи):</label><input type="text" id="avatarInput" maxlength="2" placeholder="😀">
    <label>Загрузить фото:</label><input type="file" id="avatarFile" accept="image/jpeg,image/png">
    <label>О себе:</label><textarea id="bioInput" rows="3" placeholder="О себе...">{{ bio }}</textarea>
    <label>Новое имя:</label><input type="text" id="newNameInput" placeholder="Новое имя">
    <label>Новый пароль:</label><input type="password" id="newPasswordInput" placeholder="Новый пароль">
    <button id="saveProfileBtn">💾 Сохранить</button>
</div></div>

<div id="settingsModal" class="modal"><div class="modal-content">
    <span class="close-btn" id="closeSettingsModal">&times;</span>
    <h3>⚙️ Настройки</h3>
    <button id="themeToggleBtn" style="background:#e0e7ff;">🌙 Тёмная тема</button>
    <h4 style="margin-top:20px;">📨 Заявки в друзья</h4><div id="friendRequestsList"></div>
    <h4 style="margin-top:20px;">👑 Команды в чате</h4>
    <p style="font-size:12px;">• <code>/giveadmin ИМЯ</code> — выдать админку</p>
    <p style="font-size:12px;">• <code>/unadmin ИМЯ</code> — снять админку</p>
    <p style="font-size:12px;">• <code>/addfriend ИМЯ</code> — добавить друга</p>
</div></div>

<script>
let socket=io();let currentRoom='Главная';let username='{{ username }}';let role='{{ role }}';let darkMode={{ 'true' if user_theme=='dark' else 'false' }};let typingUsers={};
const messagesDiv=document.getElementById('messagesList');const messageInput=document.getElementById('messageInput');
function applyTheme(){if(darkMode)document.body.classList.add('dark');else document.body.classList.remove('dark');}
applyTheme();
document.getElementById('themeToggleBtn')?.addEventListener('click',()=>{darkMode=!darkMode;applyTheme();fetch('/save_theme',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({theme:darkMode?'dark':'light'})});});
const profileModal=document.getElementById('profileModal');const settingsModal=document.getElementById('settingsModal');
document.getElementById('profileBtn')?.addEventListener('click',()=>profileModal.style.display='flex');
document.getElementById('settingsBtn')?.addEventListener('click',()=>{settingsModal.style.display='flex';loadFriendRequests();});
document.getElementById('closeProfileModal')?.addEventListener('click',()=>profileModal.style.display='none');
document.getElementById('closeSettingsModal')?.addEventListener('click',()=>settingsModal.style.display='none');
window.onclick=(e)=>{if(e.target===profileModal)profileModal.style.display='none';if(e.target===settingsModal)settingsModal.style.display='none';};
let tempAvatar=null;
document.getElementById('avatarFile')?.addEventListener('change',function(e){const file=e.target.files[0];if(file&&(file.type==='image/jpeg'||file.type==='image/png')){const reader=new FileReader();reader.onload=(ev)=>{tempAvatar=ev.target.result;};reader.readAsDataURL(file);}});
document.getElementById('saveProfileBtn')?.addEventListener('click',()=>{fetch('/update_profile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({avatar_emoji:document.getElementById('avatarInput').value,avatar_base64:tempAvatar,bio:document.getElementById('bioInput').value,new_name:document.getElementById('newNameInput').value,new_password:document.getElementById('newPasswordInput').value})}).then(res=>res.json()).then(data=>{if(data.success){alert('Профиль обновлён! Страница перезагрузится.');location.reload();}else alert('Ошибка: '+data.error);});});
function loadFriendRequests(){fetch('/get_friend_requests').then(r=>r.json()).then(data=>{const c=document.getElementById('friendRequestsList');if(data.requests&&data.requests.length){c.innerHTML=data.requests.map(r=>`<div style="display:flex;justify-content:space-between;margin:5px 0;"><span>📨 ${escapeHtml(r)}</span><button onclick="acceptFriend('${escapeHtml(r)}')" style="background:#10b981;border:none;border-radius:16px;padding:2px 12px;color:#fff;">Принять</button></div>`).join('');}else c.innerHTML='<p>Нет заявок</p>';});}
window.acceptFriend=(name)=>{fetch('/accept_friend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({friend:name})}).then(r=>r.json()).then(data=>{alert(data.message);loadFriendRequests();});};
function addMessage(id,name,text,time,isOwn,avatar,avatarBase64){let div=document.createElement('div');div.className=`message ${isOwn?'message-own':''}`;let avatarHtml=avatarBase64?`<img src="${avatarBase64}" style="width:100%;height:100%;">`:(avatar||'👤');div.innerHTML=`<div class="message-avatar" onclick="showUserProfile('${escapeHtml(name)}')">${avatarHtml}</div><div class="message-content"><div class="message-name">${escapeHtml(name)}<span class="message-time">${time}</span></div><div class="message-text">${escapeHtml(text)}</div></div>`;messagesDiv.appendChild(div);messagesDiv.scrollTop=messagesDiv.scrollHeight;}
window.showUserProfile=(name)=>{fetch('/get_user_info/'+encodeURIComponent(name)).then(r=>r.json()).then(data=>{alert(`${data.username}\\n📝 ${data.bio||'Нет описания'}\\n👫 Друзья: ${data.friends_count||0}\\n⭐ ${data.role_display}`);});};
function addSystemMessage(text){let div=document.createElement('div');div.className='system-msg';div.textContent=text;messagesDiv.appendChild(div);messagesDiv.scrollTop=messagesDiv.scrollHeight;}
function escapeHtml(str){return str.replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'})[m]);}
socket.emit('join',{room:currentRoom});
socket.on('history',(history)=>{messagesDiv.innerHTML='';history.forEach(msg=>addMessage(msg.id,msg.name,msg.text,msg.time,msg.name===username,msg.avatar,msg.avatar_base64));});
socket.on('new_message',(msg)=>addMessage(msg.id,msg.name,msg.text,msg.time,msg.name===username,msg.avatar,msg.avatar_base64));
socket.on('system_message',(data)=>addSystemMessage(data.text));
socket.on('rooms_update',(roomsList)=>{const c=document.getElementById('roomsList');c.innerHTML=roomsList.map(r=>`<div class="room-item ${r===currentRoom?'active':''}" data-room="${r}">🏠 ${escapeHtml(r)}</div>`).join('');document.querySelectorAll('.room-item').forEach(el=>{el.onclick=()=>{let nr=el.dataset.room;if(nr===currentRoom)return;socket.emit('switch_room',{old_room:currentRoom,new_room:nr});currentRoom=nr;document.getElementById('currentRoomSpan').innerText=currentRoom;document.querySelectorAll('.room-item').forEach(i=>i.classList.remove('active'));el.classList.add('active');messagesDiv.innerHTML='<div class="system-msg">⏳ Загрузка...</div>';};});});
socket.on('users_update',(usersList)=>{const c=document.getElementById('usersList');c.innerHTML=usersList.map(u=>`<div class="user-item" onclick="showUserProfile('${escapeHtml(u.name)}')"><span class="online-dot"></span> ${u.avatar_base64?`<img src="${u.avatar_base64}" style="width:20px;height:20px;border-radius:50%;">`:(u.avatar||'👤')} ${escapeHtml(u.name)} ${u.role==='owner'?'<span class="badge-owner">ВЛ</span>':(u.role==='admin'?'<span class="badge-admin">АДМ</span>':'')}</div>`).join('');document.getElementById('onlineCount').innerText=`👥 ${usersList.length}`;});
socket.on('friends_update',(friendsList)=>{const c=document.getElementById('friendsList');if(c)c.innerHTML=friendsList.map(f=>`<div class="user-item" onclick="showUserProfile('${escapeHtml(f.name)}')">👫 ${escapeHtml(f.name)}</div>`).join('');});
socket.on('typing_status',(data)=>{if(data.typing)typingUsers[data.name]=true;else delete typingUsers[data.name];let names=Object.keys(typingUsers).filter(n=>n!==username);document.getElementById('typingStatus').innerText=names.length?(names.length===1?`${names[0]} печатает...`:`${names.length} человек печатают...`):'';});
document.getElementById('sendBtn').onclick=()=>{let text=messageInput.value.trim();if(text){if(text.startsWith('/giveadmin ')&&role==='owner'){let target=text.split(' ')[1];fetch('/give_admin',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:target})}).then(r=>r.json()).then(data=>addSystemMessage(data.message));messageInput.value='';return;}if(text.startsWith('/unadmin ')&&role==='owner'){let target=text.split(' ')[1];fetch('/remove_admin',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:target})}).then(r=>r.json()).then(data=>addSystemMessage(data.message));messageInput.value='';return;}if(text.startsWith('/addfriend ')){let target=text.split(' ')[1];fetch('/add_friend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({friend:target})}).then(r=>r.json()).then(data=>addSystemMessage(data.message));messageInput.value='';return;}socket.emit('send_message',{text:text,room:currentRoom});messageInput.value='';}};
messageInput.onkeypress=(e)=>{if(e.key==='Enter')document.getElementById('sendBtn').click();socket.emit('typing',{room:currentRoom,typing:true});clearTimeout(window.typingTimeout);window.typingTimeout=setTimeout(()=>socket.emit('typing',{room:currentRoom,typing:false}),1000);};
document.getElementById('createRoomBtn')?.addEventListener('click',()=>{let nr=document.getElementById('newRoomName').value.trim();if(nr){socket.emit('create_room',{room:nr});document.getElementById('newRoomName').value='';}});
document.getElementById('logoutBtn')?.addEventListener('click',()=>window.location.href='/logout');
socket.emit('get_rooms');socket.emit('get_users');
</script>
</body>
</html>
'''

# ========== SOCKETIO СОБЫТИЯ ==========
@socketio.on('join')
def handle_join(data):
    username, user = get_user()
    if not username:
        return
    room = data['room']
