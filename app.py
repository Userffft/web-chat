from flask import Flask, render_template_string, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import os
import json
import hashlib

app = Flask(__name__)
app.secret_key = 'secret-key-2024'
socketio = SocketIO(app, cors_allowed_origins="*")

# === ДАННЫЕ ===
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

# === ШАБЛОНЫ ===
LOGIN = '''
<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Чатик</title><style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}.card{background:rgba(255,255,255,0.95);border-radius:48px;padding:48px;max-width:400px;width:100%;box-shadow:0 25px 50px -12px rgba(0,0,0,0.25)}h1{text-align:center;background:linear-gradient(135deg,#667eea,#764ba2);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:8px}.subtitle{text-align:center;color:#6b7280;margin-bottom:32px}input{width:100%;padding:16px;border:2px solid #e5e7eb;border-radius:32px;margin-bottom:16px;outline:none}input:focus{border-color:#667eea}button{width:100%;padding:16px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border:none;border-radius:32px;cursor:pointer}.error{background:#fee2e2;color:#dc2626;padding:12px;border-radius:24px;margin-bottom:20px;text-align:center}.footer{text-align:center;margin-top:24px;color:#6b7280}a{color:#667eea;text-decoration:none}
</style></head>
<body><div class="card"><h1>💬 Чатик</h1><div class="subtitle">Общайся с друзьями</div>{% if error %}<div class="error">{{ error }}</div>{% endif %}<form method="post"><input type="text" name="username" placeholder="Имя" required autofocus><input type="password" name="password" placeholder="Пароль" required><button type="submit">Войти</button></form><div class="footer">Нет аккаунта? <a href="/register">Регистрация</a></div></div></body></html>
'''

REG = '''
<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Регистрация</title><style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}.card{background:rgba(255,255,255,0.95);border-radius:48px;padding:48px;max-width:400px;width:100%;box-shadow:0 25px 50px -12px rgba(0,0,0,0.25)}h1{text-align:center;margin-bottom:32px;background:linear-gradient(135deg,#667eea,#764ba2);-webkit-background-clip:text;-webkit-text-fill-color:transparent}input{width:100%;padding:16px;border:2px solid #e5e7eb;border-radius:32px;margin-bottom:16px;outline:none}input:focus{border-color:#667eea}button{width:100%;padding:16px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border:none;border-radius:32px;cursor:pointer}.error{background:#fee2e2;color:#dc2626;padding:12px;border-radius:24px;margin-bottom:20px;text-align:center}.footer{text-align:center;margin-top:24px;color:#6b7280}a{color:#667eea;text-decoration:none}
</style></head>
<body><div class="card"><h1>📝 Регистрация</h1>{% if error %}<div class="error">{{ error }}</div>{% endif %}<form method="post"><input type="text" name="username" placeholder="Имя (3-20)" required autofocus><input type="password" name="password" placeholder="Пароль (мин 4)" required><button type="submit">Создать</button></form><div class="footer">Уже есть? <a href="/login">Войти</a></div></div></body></html>
'''

CHAT = '''
<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Чатик · {{ username }}</title><script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script><style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:linear-gradient(135deg,#1e1b4b,#4c1d95);height:100vh;display:flex}body.dark{background:#0f172a}.sidebar{width:280px;background:rgba(255,255,255,0.95);backdrop-filter:blur(10px);border-right:1px solid rgba(0,0,0,0.1);display:flex;flex-direction:column;overflow-y:auto}body.dark .sidebar{background:#1e293b;color:#fff}.user-card{text-align:center;padding:24px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;cursor:pointer}.user-avatar{font-size:64px}.user-name{font-size:18px;font-weight:700}.section-title{font-weight:600;padding:16px 20px 8px 20px;color:#475569;font-size:12px;text-transform:uppercase}body.dark .section-title{color:#94a3b8}.room-item,.user-item{padding:12px 20px;margin:4px 12px;border-radius:16px;cursor:pointer;display:flex;align-items:center;gap:12px}.room-item:hover,.user-item:hover{background:rgba(0,0,0,0.05)}body.dark .room-item:hover,body.dark .user-item:hover{background:rgba(255,255,255,0.05)}.room-item.active{background:#4f46e5;color:#fff}.add-room{display:flex;gap:8px;margin:12px}.add-room input{flex:1;padding:10px;border-radius:40px;border:1px solid #ddd;outline:none}body.dark .add-room input{background:#334155;color:#fff;border-color:#475569}.add-room button{background:#4f46e5;color:#fff;border:none;border-radius:40px;padding:8px 20px;cursor:pointer}.chat-area{flex:1;display:flex;flex-direction:column;background:#fff}body.dark .chat-area{background:#0f172a}.chat-header{padding:20px 24px;background:#fff;border-bottom:1px solid #e2e8f0;display:flex;justify-content:space-between}body.dark .chat-header{background:#1e293b;color:#fff}.messages{flex:1;overflow-y:auto;padding:24px;display:flex;flex-direction:column;gap:16px}.message{display:flex;gap:12px;align-items:flex-start}.message-own{justify-content:flex-end}.message-avatar{width:40px;height:40px;background:linear-gradient(135deg,#667eea,#764ba2);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:20px;cursor:pointer}.message-content{background:#f1f5f9;padding:10px 16px;border-radius:20px;max-width:65%}body.dark .message-content{background:#334155;color:#fff}.message-own .message-content{background:#4f46e5;color:#fff}.message-name{font-weight:700;font-size:13px}.message-time{font-size:10px;opacity:0.6;margin-left:8px}.message-text{margin-top:4px}.badge-owner{background:#ef4444;font-size:9px;padding:2px 8px;border-radius:20px;margin-left:6px}.badge-admin{background:#10b981;font-size:9px;padding:2px 8px;border-radius:20px;margin-left:6px}.online-dot{width:10px;height:10px;background:#10b981;border-radius:50%;display:inline-block;margin-right:8px}.system-msg{text-align:center;font-size:12px;color:#64748b;padding:8px}.typing{padding:8px 24px;font-size:12px;color:#64748b;font-style:italic}.input-area{display:flex;gap:12px;padding:20px 24px;background:#fff;border-top:1px solid #e2e8f0}body.dark .input-area{background:#1e293b}.input-area input{flex:1;padding:14px 20px;border:2px solid #e2e8f0;border-radius:40px;outline:none}body.dark .input-area input{background:#334155;color:#fff;border-color:#475569}.input-area button{background:#4f46e5;border:none;border-radius:50%;width:48px;height:48px;color:#fff;cursor:pointer}.btn-settings,.btn-logout{margin:8px 12px;padding:12px;border-radius:20px;cursor:pointer;border:none}.btn-settings{background:#e0e7ff;color:#4f46e5}.btn-logout{background:#fee2e2;color:#dc2626}body.dark .btn-settings{background:#334155;color:#818cf8}body.dark .btn-logout{background:#334155;color:#f87171}.modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);align-items:center;justify-content:center;z-index:1000}.modal-content{background:#fff;border-radius:32px;padding:32px;max-width:400px;width:90%}body.dark .modal-content{background:#1e293b;color:#fff}.modal-content input,.modal-content textarea{width:100%;padding:12px;margin:10px 0;border-radius:24px;border:1px solid #ddd;outline:none}.modal-content button{background:#4f46e5;color:#fff;border:none;padding:12px;border-radius:24px;width:100%;cursor:pointer}.close{float:right;font-size:28px;cursor:pointer}.user-menu{position:fixed;background:#fff;border-radius:16px;box-shadow:0 10px 25px rgba(0,0,0,0.1);padding:8px;z-index:1000;display:none;min-width:160px}body.dark .user-menu{background:#1e293b}.user-menu button{width:100%;padding:10px 16px;border:none;background:none;text-align:left;cursor:pointer;border-radius:12px}.user-menu button:hover{background:#f1f5f9}body.dark .user-menu button:hover{background:#334155;color:#fff}.emoji-picker{position:absolute;bottom:80px;left:20px;background:#fff;border-radius:20px;padding:12px;display:none;grid-template-columns:repeat(6,1fr);gap:8px;box-shadow:0 10px 25px rgba(0,0,0,0.1);z-index:1000}body.dark .emoji-picker{background:#1e293b}.emoji{font-size:24px;cursor:pointer;text-align:center;padding:5px;border-radius:12px}.emoji:hover{background:#f1f5f9}@media(max-width:680px){.sidebar{width:260px}}
</style></head>
<body><div class="sidebar"><div class="user-card" id="profileBtn"><div class="user-avatar">{{ avatar }}</div><div class="user-name">{{ username }}{% if role == 'owner' %}<span class="badge-owner">ВЛ</span>{% elif role == 'admin' %}<span class="badge-admin">АДМ</span>{% endif %}</div><div class="user-bio" style="font-size:12px">{{ bio[:40] }}</div></div><div class="section-title">🏠 КОМНАТЫ</div><div id="roomsList"></div>{% if role in ['owner','admin'] %}<div class="add-room"><input id="newRoom" placeholder="Название"><button id="createRoomBtn">+</button></div>{% endif %}<div class="section-title">👥 ОНЛАЙН</div><div id="usersList"></div><div class="section-title">👫 ДРУЗЬЯ</div><div id="friendsList"></div><button class="btn-settings" id="settingsBtn">⚙️ Настройки</button><button class="btn-logout" id="logoutBtn">🚪 Выйти</button></div><div class="chat-area"><div class="chat-header"><span><strong>#</strong> <span id="roomName">Главная</span></span><span id="onlineCount"></span></div><div id="messagesList" class="messages"></div><div id="typingStatus" class="typing"></div><div class="input-area"><button id="emojiBtn">😊</button><input id="messageInput" placeholder="Сообщение..."><button id="sendBtn">📤</button></div></div>

<div id="emojiPicker" class="emoji-picker"></div>
<div id="profileModal" class="modal"><div class="modal-content"><span class="close" id="closeProfile">&times;</span><h3>👤 Мой профиль</h3><label>Аватар (эмодзи):</label><input id="avatarInput" maxlength="2" placeholder="😀"><label>О себе:</label><textarea id="bioInput" rows="3">{{ bio }}</textarea><label>Новое имя:</label><input id="newName" placeholder="Новое имя"><label>Новый пароль:</label><input type="password" id="newPass" placeholder="Новый пароль"><button id="saveProfile">💾 Сохранить</button></div></div>
<div id="settingsModal" class="modal"><div class="modal-content"><span class="close" id="closeSettings">&times;</span><h3>⚙️ Настройки</h3><button id="themeBtn">🌙 Тёмная тема</button><h4 style="margin-top:20px">📨 Заявки</h4><div id="requestsList"></div><h4 style="margin-top:20px">👑 Команды</h4><p style="font-size:12px">• <code>/giveadmin ИМЯ</code> — выдать админку</p><p style="font-size:12px">• <code>/unadmin ИМЯ</code> — снять админку</p></div></div>
<div id="userMenu" class="user-menu"></div>

<script>
let socket=io(),currentRoom='Главная',username='{{ username }}',role='{{ role }}',dark=false,typingUsers={};
const msgDiv=document.getElementById('messagesList'),msgInput=document.getElementById('messageInput');
const emojis=['😀','😂','❤️','👍','🎉','🔥','😍','🥹','😭','🤔','👋','🙏','✨','💯','😎','🥳'];
const picker=document.getElementById('emojiPicker');
picker.innerHTML=emojis.map(e=>`<div class="emoji">${e}</div>`).join('');
document.querySelectorAll('.emoji').forEach(el=>el.onclick=()=>{msgInput.value+=el.textContent;msgInput.focus();picker.style.display='none';});
document.getElementById('emojiBtn').onclick=()=>picker.style.display=picker.style.display==='grid'?'none':'grid';
document.addEventListener('click',e=>{if(!e.target.closest('#emojiBtn')&&!e.target.closest('.emoji-picker'))picker.style.display='none';if(!e.target.closest('.user-item')&&!e.target.closest('.user-menu'))document.getElementById('userMenu').style.display='none';});
function showUserMenu(name,x,y){
    let menu=document.getElementById('userMenu');
    fetch('/user_info/'+encodeURIComponent(name)).then(r=>r.json()).then(data=>{
        menu.innerHTML=`<button onclick="viewProfile('${name}')">👤 Профиль</button>${!data.is_friend&&name!==username?`<button onclick="addFriend('${name}')">➕ В друзья</button>`:''}${data.is_friend?`<button onclick="removeFriend('${name}')">❌ Удалить</button>`:''}${role==='owner'||role==='admin'?`<button onclick="giveAdmin('${name}')">⭐ Выдать админку</button>`:''}`;
        menu.style.display='block';menu.style.left=x+'px';menu.style.top=y+'px';
        setTimeout(()=>{if(menu.style.display==='block')menu.style.display='none';},5000);
    });
}
window.viewProfile=name=>fetch('/user_info/'+encodeURIComponent(name)).then(r=>r.json()).then(data=>alert(`${data.username}\n📝 ${data.bio||'Нет'}\n👫 Друзья: ${data.friends_count}\n⭐ ${data.role_display}`));
window.addFriend=name=>fetch('/add_friend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({friend:name})}).then(r=>r.json()).then(data=>addSystem(data.message));
window.removeFriend=name=>fetch('/remove_friend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({friend:name})}).then(r=>r.json()).then(data=>addSystem(data.message));
window.giveAdmin=name=>{fetch('/give_admin',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:name})}).then(r=>r.json()).then(data=>addSystem(data.message));document.getElementById('userMenu').style.display='none';};
function loadRequests(){fetch('/get_requests').then(r=>r.json()).then(data=>{let d=document.getElementById('requestsList');if(data.requests&&data.requests.length)d.innerHTML=data.requests.map(r=>`<div style="display:flex;justify-content:space-between;margin:8px 0"><span>📨 ${escape(r)}</span><button onclick="acceptReq('${escape(r)}')" style="background:#10b981;border:none;border-radius:16px;padding:4px 12px;color:#fff">Принять</button></div>`).join('');else d.innerHTML='<p>Нет заявок</p>';});}
window.acceptReq=name=>fetch('/accept_friend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({friend:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);loadRequests();});
function addMessage(id,name,text,time,own,avatar){let div=document.createElement('div');div.className=`message ${own?'message-own':''}`;div.innerHTML=`<div class="message-avatar">${avatar||'👤'}</div><div class="message-content"><div class="message-name">${escape(name)}<span class="message-time">${time}</span></div><div class="message-text">${escape(text)}</div></div>`;msgDiv.appendChild(div);msgDiv.scrollTop=msgDiv.scrollHeight;}
function addSystem(t){let d=document.createElement('div');d.className='system-msg';d.textContent=t;msgDiv.appendChild(d);msgDiv.scrollTop=msgDiv.scrollHeight;}
function escape(s){return s.replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'})[m]);}
socket.emit('join',{room:currentRoom});
socket.on('history',h=>{msgDiv.innerHTML='';h.forEach(m=>addMessage(m.id,m.name,m.text,m.time,m.name===username,m.avatar));});
socket.on('message',m=>addMessage(m.id,m.name,m.text,m.time,m.name===username,m.avatar));
socket.on('system',d=>addSystem(d.text));
socket.on('rooms',l=>{let c=document.getElementById('roomsList');c.innerHTML=l.map(r=>`<div class="room-item ${r===currentRoom?'active':''}" data-room="${r}">🏠 ${escape(r)}</div>`).join('');document.querySelectorAll('.room-item').forEach(el=>{el.onclick=()=>{let nr=el.dataset.room;if(nr===currentRoom)return;socket.emit('switch',{old:currentRoom,new:nr});currentRoom=nr;document.getElementById('roomName').innerText=currentRoom;document.querySelectorAll('.room-item').forEach(i=>i.classList.remove('active'));el.classList.add('active');msgDiv.innerHTML='<div class="system-msg">⏳ Загрузка...</div>';};});});
socket.on('users',l=>{let c=document.getElementById('usersList');c.innerHTML=l.map(u=>`<div class="user-item" data-user="${escape(u.name)}" onclick="showUserMenu('${escape(u.name)}', event.clientX, event.clientY)"><span class="online-dot"></span> ${u.avatar||'👤'} ${escape(u.name)} ${u.role==='owner'?'<span class="badge-owner">ВЛ</span>':(u.role==='admin'?'<span class="badge-admin">АДМ</span>':'')}</div>`).join('');document.getElementById('onlineCount').innerText=`👥 ${l.length}`;});
socket.on('friends',l=>{let c=document.getElementById('friendsList');if(c)c.innerHTML=l.map(f=>`<div class="user-item" onclick="viewProfile('${escape(f.name)}')">👫 ${escape(f.name)}</div>`).join('');});
socket.on('typing',d=>{if(d.typing)typingUsers[d.name]=true;else delete typingUsers[d.name];let n=Object.keys(typingUsers).filter(n=>n!==username);document.getElementById('typingStatus').innerText=n.length?(n.length===1?`${n[0]} печатает...`:`${n.length} человек печатают...`):'';});
document.getElementById('sendBtn').onclick=()=>{let t=msgInput.value.trim();if(!t)return;if(t.startsWith('/giveadmin ')&&role==='owner'){let target=t.split(' ')[1];fetch('/give_admin',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:target})}).then(r=>r.json()).then(data=>addSystem(data.message));msgInput.value='';return;}if(t.startsWith('/unadmin ')&&role==='owner'){let target=t.split(' ')[1];fetch('/remove_admin',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:target})}).then(r=>r.json()).then(data=>addSystem(data.message));msgInput.value='';return;}socket.emit('message',{text:t,room:currentRoom});msgInput.value='';};
msgInput.onkeypress=e=>{if(e.key==='Enter')document.getElementById('sendBtn').click();socket.emit('typing',{room:currentRoom,typing:true});clearTimeout(window.tt);window.tt=setTimeout(()=>socket.emit('typing',{room:currentRoom,typing:false}),1000);};
document.getElementById('createRoomBtn')?.addEventListener('click',()=>{let n=document.getElementById('newRoom').value.trim();if(n){socket.emit('create',{room:n});document.getElementById('newRoom').value='';}});
document.getElementById('profileBtn').onclick=()=>document.getElementById('profileModal').style.display='flex';
document.getElementById('settingsBtn').onclick=()=>{document.getElementById('settingsModal').style.display='flex';loadRequests();};
document.getElementById('closeProfile').onclick=()=>document.getElementById('profileModal').style.display='none';
document.getElementById('closeSettings').onclick=()=>document.getElementById('settingsModal').style.display='none';
window.onclick=e=>{if(e.target===document.getElementById('profileModal'))document.getElementById('profileModal').style.display='none';if(e.target===document.getElementById('settingsModal'))document.getElementById('settingsModal').style.display='none';};
document.getElementById('saveProfile').onclick=()=>{fetch('/update_profile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({avatar:document.getElementById('avatarInput').value,bio:document.getElementById('bioInput').value,new_name:document.getElementById('newName').value,new_password:document.getElementById('newPass').value})}).then(r=>r.json()).then(data=>{if(data.success){alert('Сохранено! Страница перезагрузится.');location.reload();}else alert('Ошибка: '+data.error);});};
document.getElementById('themeBtn').onclick=()=>{dark=!dark;if(dark)document.body.classList.add('dark');else document.body.classList.remove('dark');fetch('/save_theme',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({theme:dark?'dark':'light'})});};
document.getElementById('logoutBtn').onclick=()=>window.location.href='/logout';
socket.emit('get_rooms');socket.emit('get_users');
</script>
</body></html>
'''

# === МАРШРУТЫ ===
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    u = users.get(session['username'])
    if not u or u.get('banned'):
        session.clear()
        return redirect(url_for('login'))
    return render_template_string(CHAT, username=session['username'], role=u['role'], avatar=u.get('avatar','👤'), bio=u.get('bio',''))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        name = request.form['username']
        pwd = request.form['password']
        h = hashlib.sha256(pwd.encode()).hexdigest()
        if name in users and users[name]['password'] == h:
            if users[name].get('banned'):
                return render_template_string(LOGIN, error='Заблокирован')
            session['username'] = name
            return redirect(url_for('index'))
        return render_template_string(LOGIN, error='Неверные данные')
    return render_template_string(LOGIN)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['username']
        pwd = request.form['password']
        if name in users:
            return render_template_string(REG, error='Имя занято')
        if len(name) < 3 or len(name) > 20:
            return render_template_string(REG, error='Имя 3-20')
        if len(pwd) < 4:
            return render_template_string(REG, error='Пароль мин 4')
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
    return render_template_string(REG)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/save_theme', methods=['POST'])
def save_theme():
    if 'username' in session:
        users[session['username']]['theme'] = request.json.get('theme', 'light')
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
            return jsonify({'error': 'Имя 3-20'}), 400
        if nn in users and nn != name:
            return jsonify({'error': 'Имя занято'}), 400
        users[nn] = users.pop(name)
        session['username'] = nn
        name = nn
    if data.get('new_password') and len(data['new_password']) >= 4:
        users[name]['password'] = hashlib.sha256(data['new_password'].encode()).hexdigest()
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

@app.route('/remove_friend', methods=['POST'])
def remove_friend():
    if 'username' not in session:
        return jsonify({'message': 'Войдите'})
    name = session['username']
    target = request.json.get('friend')
    if target in users[name]['friends']:
        users[name]['friends'].remove(target)
        users[target]['friends'].remove(name)
        save_users(users)
        return jsonify({'message': f'{target} удалён из друзей'})
    return jsonify({'message': 'Не в друзьях'})

@app.route('/get_requests')
def get_requests():
    if 'username' not in session:
        return jsonify({'requests': []})
    return jsonify
