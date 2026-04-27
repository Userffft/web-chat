from flask import Flask, render_template_string, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import os
import json
import hashlib

app = Flask(__name__)
app.secret_key = 'secret-key-2024'
socketio = SocketIO(app, cors_allowed_origins="*")

USERS_FILE = 'users.json'
MESSAGES_FILE = 'messages.json'
ROOMS_FILE = 'rooms.json'

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {
        'MrAizex': {'password': hashlib.sha256('admin123'.encode()).hexdigest(), 'role': 'owner', 'avatar': '👑', 'bio': 'Владелец чата', 'friends': [], 'requests': [], 'banned': False, 'theme': 'light'},
        'dimooon': {'password': hashlib.sha256('1111'.encode()).hexdigest(), 'role': 'admin', 'avatar': '😎', 'bio': 'Администратор', 'friends': [], 'requests': [], 'banned': False, 'theme': 'light'}
    }

def save_users(u):
    with open(USERS_FILE, 'w') as f:
        json.dump(u, f)

def load_messages():
    if os.path.exists(MESSAGES_FILE):
        return json.load(open(MESSAGES_FILE))
    return {'Главная': []}

def save_messages(m):
    with open(MESSAGES_FILE, 'w') as f:
        json.dump(m, f)

def load_rooms():
    if os.path.exists(ROOMS_FILE):
        return json.load(open(ROOMS_FILE))
    return ['Главная', 'Случайная', 'Помощь']

def save_rooms(r):
    with open(ROOMS_FILE, 'w') as f:
        json.dump(r, f)

users = load_users()
messages = load_messages()
rooms = load_rooms()

LOGIN_HTML = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Вход в Чатик</title><style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Segoe UI',system-ui;background:linear-gradient(135deg,#0f172a,#1e1b4b);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}.card{background:rgba(255,255,255,0.1);backdrop-filter:blur(16px);border-radius:48px;padding:40px;max-width:400px;width:100%;text-align:center;border:1px solid rgba(255,255,255,0.2);box-shadow:0 25px 50px -12px rgba(0,0,0,0.5)}h1{color:#fff;margin-bottom:8px;font-size:32px}.subtitle{color:#cbd5e1;margin-bottom:32px}input{width:100%;padding:16px;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);border-radius:32px;margin-bottom:16px;color:#fff;font-size:16px;outline:none}input:focus{border-color:#8b5cf6}input::placeholder{color:#94a3b8}button{width:100%;padding:16px;background:linear-gradient(135deg,#8b5cf6,#6366f1);color:#fff;border:none;border-radius:32px;font-size:16px;font-weight:600;cursor:pointer;transition:0.2s}button:hover{transform:translateY(-2px)}.error{background:rgba(239,68,68,0.2);color:#fecaca;padding:12px;border-radius:24px;margin-bottom:20px;border:1px solid rgba(239,68,68,0.3)}.footer{margin-top:24px;color:#94a3b8}a{color:#a78bfa;text-decoration:none}
</style>
</head>
<body><div class="card"><h1>💬 Чатик</h1><div class="subtitle">Общайся с друзьями</div>{% if error %}<div class="error">{{ error }}</div>{% endif %}<form method="post"><input type="text" name="username" placeholder="Имя" required autofocus><input type="password" name="password" placeholder="Пароль" required><button type="submit">Войти</button></form><div class="footer">Нет аккаунта? <a href="/register">Регистрация</a></div></div></body>
</html>
'''

REGISTER_HTML = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Регистрация в Чатик</title><style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Segoe UI',system-ui;background:linear-gradient(135deg,#0f172a,#1e1b4b);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}.card{background:rgba(255,255,255,0.1);backdrop-filter:blur(16px);border-radius:48px;padding:40px;max-width:400px;width:100%;text-align:center;border:1px solid rgba(255,255,255,0.2);box-shadow:0 25px 50px -12px rgba(0,0,0,0.5)}h1{color:#fff;margin-bottom:32px}input{width:100%;padding:16px;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);border-radius:32px;margin-bottom:16px;color:#fff;font-size:16px;outline:none}input:focus{border-color:#8b5cf6}input::placeholder{color:#94a3b8}button{width:100%;padding:16px;background:linear-gradient(135deg,#8b5cf6,#6366f1);color:#fff;border:none;border-radius:32px;font-size:16px;font-weight:600;cursor:pointer;transition:0.2s}button:hover{transform:translateY(-2px)}.error{background:rgba(239,68,68,0.2);color:#fecaca;padding:12px;border-radius:24px;margin-bottom:20px}.footer{margin-top:24px;color:#94a3b8}a{color:#a78bfa;text-decoration:none}
</style>
</head>
<body><div class="card"><h1>📝 Регистрация</h1>{% if error %}<div class="error">{{ error }}</div>{% endif %}<form method="post"><input type="text" name="username" placeholder="Имя (3-20)" required autofocus><input type="password" name="password" placeholder="Пароль (мин 4)" required><button type="submit">Создать</button></form><div class="footer">Уже есть? <a href="/login">Войти</a></div></div></body>
</html>
'''

CHAT_HTML = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes"><title>Чатик · {{ username }}</title><script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script><style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Segoe UI',system-ui;background:linear-gradient(135deg,#0f172a,#1e1b4b);height:100vh;display:flex;overflow:hidden}.app{display:flex;width:100%;height:100%}.sidebar{width:280px;background:rgba(15,23,42,0.9);backdrop-filter:blur(12px);border-right:1px solid rgba(255,255,255,0.1);display:flex;flex-direction:column;overflow-y:auto}.user-card{text-align:center;padding:24px;background:linear-gradient(135deg,#8b5cf6,#6366f1);color:#fff;cursor:pointer;margin:16px;border-radius:28px}.user-avatar{font-size:56px}.user-name{font-size:18px;font-weight:700;margin-top:4px}.user-bio{font-size:11px;opacity:0.8;margin-top:5px}.section-title{font-weight:600;padding:16px 20px 8px 20px;color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:1px}.room-item,.user-item{padding:12px 20px;margin:4px 12px;border-radius:16px;cursor:pointer;display:flex;align-items:center;gap:12px;transition:0.2s;color:#e2e8f0}.room-item:hover,.user-item:hover{background:rgba(139,92,246,0.2)}.room-item.active{background:#8b5cf6;color:#fff}.add-room{display:flex;gap:8px;margin:12px}.add-room input{flex:1;padding:10px;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);border-radius:40px;outline:none;color:#fff}.add-room input::placeholder{color:#64748b}.add-room button{background:#8b5cf6;color:#fff;border:none;border-radius:40px;padding:8px 20px;cursor:pointer}.chat-area{flex:1;display:flex;flex-direction:column;background:rgba(255,255,255,0.05)}.chat-header{padding:16px 24px;background:rgba(15,23,42,0.8);backdrop-filter:blur(8px);border-bottom:1px solid rgba(255,255,255,0.1);display:flex;justify-content:space-between;align-items:center;color:#fff}.messages{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:12px}.message{display:flex;gap:12px;align-items:flex-start;animation:fadeIn 0.2s}.message-own{justify-content:flex-end}@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}.message-avatar{width:40px;height:40px;background:linear-gradient(135deg,#8b5cf6,#6366f1);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:18px;cursor:pointer;flex-shrink:0}.message-content{background:rgba(255,255,255,0.1);padding:10px 16px;border-radius:20px;max-width:65%;word-break:break-word;color:#e2e8f0}.message-own .message-content{background:#8b5cf6;color:#fff}.message-name{font-weight:700;font-size:13px;display:flex;align-items:center;gap:6px;margin-bottom:4px}.message-time{font-size:9px;opacity:0.6;margin-left:6px}.message-text{font-size:14px;line-height:1.4}.badge-owner{background:#ef4444;font-size:8px;padding:2px 6px;border-radius:20px}.badge-admin{background:#10b981;font-size:8px;padding:2px 6px;border-radius:20px}.online-dot{width:8px;height:8px;background:#10b981;border-radius:50%;display:inline-block;margin-right:8px}.system-msg{text-align:center;font-size:11px;color:#94a3b8;padding:6px;margin:4px 0}.typing{padding:6px 24px;font-size:11px;color:#94a3b8;font-style:italic}.input-area{display:flex;gap:12px;padding:16px 24px;background:rgba(15,23,42,0.8);backdrop-filter:blur(8px);border-top:1px solid rgba(255,255,255,0.1)}.input-area input{flex:1;padding:14px 20px;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);border-radius:40px;outline:none;color:#fff;font-size:14px}.input-area input::placeholder{color:#64748b}.input-area button{background:#8b5cf6;border:none;border-radius:50%;width:48px;height:48px;color:#fff;cursor:pointer;font-size:18px;display:flex;align-items:center;justify-content:center;transition:0.2s}.input-area button:hover{transform:scale(1.05)}.btn-settings,.btn-logout{margin:8px 12px;padding:12px;border-radius:20px;cursor:pointer;border:none;font-weight:500}.btn-settings{background:#8b5cf6;color:#fff}.btn-logout{background:rgba(239,68,68,0.3);color:#fecaca}.modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);align-items:center;justify-content:center;z-index:1000}.modal-content{background:rgba(15,23,42,0.95);backdrop-filter:blur(16px);border-radius:28px;padding:24px;max-width:350px;width:90%;border:1px solid rgba(255,255,255,0.2)}.modal-content input,.modal-content textarea{width:100%;padding:12px;margin:8px 0;border-radius:24px;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);color:#fff;outline:none}.modal-content button{background:#8b5cf6;color:#fff;border:none;padding:12px;border-radius:24px;width:100%;cursor:pointer;margin-top:8px}.close{float:right;font-size:24px;cursor:pointer;color:#fff}.profile-avatar{font-size:64px;text-align:center;margin-bottom:12px}.profile-name{font-size:20px;font-weight:700;text-align:center;margin-bottom:4px;color:#fff}.profile-role{text-align:center;font-size:12px;color:#94a3b8;margin-bottom:16px}.profile-bio{background:rgba(255,255,255,0.1);padding:12px;border-radius:20px;margin:16px 0;font-size:14px;color:#e2e8f0}.profile-actions{display:flex;gap:10px;margin-top:16px}.profile-actions button{flex:1;padding:10px;border-radius:24px;border:none;cursor:pointer;font-weight:500}.emoji-picker{position:absolute;bottom:90px;left:20px;background:rgba(15,23,42,0.95);backdrop-filter:blur(12px);border-radius:20px;padding:12px;display:none;grid-template-columns:repeat(6,1fr);gap:8px;box-shadow:0 10px 25px rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);z-index:1000}.emoji{font-size:28px;cursor:pointer;text-align:center;padding:6px;border-radius:12px}.emoji:hover{background:rgba(139,92,246,0.3)}.friend-request-item{display:flex;justify-content:space-between;align-items:center;padding:12px;margin:8px 0;background:rgba(255,255,255,0.1);border-radius:20px;color:#e2e8f0}@media(max-width:680px){.sidebar{width:240px}}
</style>
</head>
<body><div class="app"><div class="sidebar"><div class="user-card" id="profileBtn"><div class="user-avatar">{{ avatar }}</div><div class="user-name">{{ username }}{% if role == "owner" %}<span class="badge-owner"> ВЛ</span>{% elif role == "admin" %}<span class="badge-admin"> АДМ</span>{% endif %}</div><div class="user-bio">{{ bio[:40] }}</div></div><div class="section-title">🏠 КОМНАТЫ</div><div id="roomsList"></div>{% if role in ["owner", "admin"] %}<div class="add-room"><input type="text" id="newRoom" placeholder="Название"><button id="createRoomBtn">+</button></div>{% endif %}<div class="section-title">👥 ОНЛАЙН</div><div id="usersList"></div><div class="section-title">👫 ДРУЗЬЯ</div><div id="friendsList"></div><button class="btn-settings" id="settingsBtn">⚙️ Настройки</button><button class="btn-logout" id="logoutBtn">🚪 Выйти</button></div><div class="chat-area"><div class="chat-header"><span><strong>#</strong> <span id="roomName">Главная</span></span><span id="onlineCount"></span></div><div id="messagesList" class="messages"></div><div id="typingStatus" class="typing"></div><div class="input-area"><button id="emojiBtn">😊</button><input type="text" id="messageInput" placeholder="Сообщение..."><button id="sendBtn">📤</button></div></div></div>
<div id="emojiPicker" class="emoji-picker"></div>
<div id="profileModal" class="modal"><div class="modal-content"><span class="close" id="closeProfile">&times;</span><h3 style="color:#fff;margin-bottom:16px">👤 Мой профиль</h3><label style="color:#94a3b8">Аватар:</label><input type="text" id="avatarInput" maxlength="2" placeholder="😀"><label style="color:#94a3b8">О себе:</label><textarea id="bioInput" rows="3" style="color:#fff">{{ bio }}</textarea><label style="color:#94a3b8">Новое имя:</label><input type="text" id="newName" placeholder="Новое имя"><label style="color:#94a3b8">Новый пароль:</label><input type="password" id="newPass" placeholder="Новый пароль"><button id="saveProfile">💾 Сохранить</button></div></div>
<div id="settingsModal" class="modal"><div class="modal-content"><span class="close" id="closeSettings">&times;</span><h3 style="color:#fff;margin-bottom:16px">⚙️ Настройки</h3><button id="themeBtn" style="background:#8b5cf6">🌙 Тёмная тема</button><h4 style="margin:16px 0 8px;color:#94a3b8">👑 КОМАНДЫ</h4><p style="font-size:12px;color:#e2e8f0">• /giveadmin ИМЯ — выдать админку</p><p style="font-size:12px;color:#e2e8f0">• /unadmin ИМЯ — снять админку</p><h4 style="margin:16px 0 8px;color:#94a3b8">📨 ЗАЯВКИ В ДРУЗЬЯ</h4><div id="requestsList"></div></div></div>
<div id="userModal" class="modal"><div class="modal-content"><span class="close" id="closeUserModal">&times;</span><div id="userModalContent"></div></div></div>
<script>
let socket=io(),currentRoom='Главная',username='{{ username }}',role='{{ role }}',dark=false,typingUsers={};
const msgDiv=document.getElementById('messagesList'),msgInput=document.getElementById('messageInput');
const emojis=['😀','😂','❤️','👍','🎉','🔥','😍','🥹','😭','🤔','👋','🙏','✨','💯','😎','🥳','😡','🤯','🥰','😱'];
const picker=document.getElementById('emojiPicker');
picker.innerHTML=emojis.map(e=>`<div class="emoji">${e}</div>`).join('');
document.querySelectorAll('.emoji').forEach(el=>el.onclick=()=>{msgInput.value+=el.textContent;msgInput.focus();picker.style.display='none';});
document.getElementById('emojiBtn').onclick=(e)=>{e.stopPropagation();picker.style.display=picker.style.display==='grid'?'none':'grid';};
document.addEventListener('click',(e)=>{if(!e.target.closest('#emojiBtn')&&!e.target.closest('.emoji-picker'))picker.style.display='none';});
function loadRequests(){fetch('/get_requests').then(r=>r.json()).then(data=>{let d=document.getElementById('requestsList');if(data.requests&&data.requests.length){d.innerHTML=data.requests.map(r=>`<div class="friend-request-item"><span>📨 ${escape(r)}</span><button onclick="acceptReq('${escape(r)}')" style="background:#10b981;border:none;border-radius:20px;padding:6px 14px;color:#fff;cursor:pointer">Принять</button></div>`).join('');}else d.innerHTML='<p style="color:#94a3b8;text-align:center;padding:12px">Нет заявок</p>';});}}
window.acceptReq=name=>{fetch('/accept_friend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({friend:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);loadRequests();});};
function addMessage(id,name,text,time,isOwn,avatar){let div=document.createElement('div');div.className=`message ${isOwn?'message-own':''}`;let roleBadge='';if(name==='MrAizex')roleBadge='<span class="badge-owner">ВЛ</span>';else if(name==='dimooon')roleBadge='<span class="badge-admin">АДМ</span>';div.innerHTML=`<div class="message-avatar" onclick="showUser('${escape(name)}')">${avatar||'👤'}</div><div class="message-content"><div class="message-name">${escape(name)}${roleBadge}<span class="message-time">${time}</span></div><div class="message-text">${escape(text)}</div></div>`;msgDiv.appendChild(div);msgDiv.scrollTop=msgDiv.scrollHeight;}
function addSystem(t){let d=document.createElement('div');d.className='system-msg';d.textContent=t;msgDiv.appendChild(d);msgDiv.scrollTop=msgDiv.scrollHeight;}
function escape(s){return s.replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'})[m]);}
function showUser(name){fetch('/user_info/'+encodeURIComponent(name)).then(r=>r.json()).then(data=>{let actions='';if(!data.is_friend&&name!==username)actions+=`<button onclick="addFriendFromModal('${name}')" style="background:#8b5cf6;color:#fff">➕ В друзья</button>`;if(data.is_friend)actions+=`<button onclick="removeFriendFromModal('${name}')" style="background:#ef4444;color:#fff">❌ Удалить из друзей</button>`;if(role==='owner'||role==='admin'){if(data.user_role==='admin')actions+=`<button onclick="unadminUser('${name}')" style="background:#f59e0b;color:#fff">🔻 Снять админку</button>`;else if(data.user_role!=='owner')actions+=`<button onclick="giveAdminFromModal('${name}')" style="background:#10b981;color:#fff">⭐ Выдать админку</button>`;}document.getElementById('userModalContent').innerHTML=`<div class="profile-avatar">${data.avatar||'👤'}</div><div class="profile-name">${escape(data.username)}</div><div class="profile-role">${data.role_display}</div><div class="profile-bio">📝 ${escape(data.bio||'Нет описания')}</div><div class="profile-actions">${actions}</div>`;document.getElementById('userModal').style.display='flex';});}
window.addFriendFromModal=name=>{fetch('/add_friend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({friend:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);document.getElementById('userModal').style.display='none';});};
window.removeFriendFromModal=name=>{fetch('/remove_friend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({friend:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);document.getElementById('userModal').style.display='none';});};
window.giveAdminFromModal=name=>{fetch('/give_admin',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);document.getElementById('userModal').style.display='none';});};
window.unadminUser=name=>{fetch('/remove_admin',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);document.getElementById('userModal').style.display='none';});};
socket.emit('join',{room:currentRoom});
socket.on('history',h=>{msgDiv.innerHTML='';h.forEach(m=>addMessage(m.id,m.name,m.text,m.time,m.name===username,m.avatar));});
socket.on('message',m=>addMessage(m.id,m.name,m.text,m.time,m.name===username,m.avatar));
socket.on('system',d=>addSystem(d.text));
socket.on('rooms',l=>{let c=document.getElementById('roomsList');c.innerHTML=l.map(r=>`<div class="room-item ${r===currentRoom?'active':''}" data-room="${r}">🏠 ${escape(r)}</div>`).join('');document.querySelectorAll('.room-item').forEach(el=>{el.onclick=()=>{let nr=el.dataset.room;if(nr===currentRoom)return;socket.emit('switch',{old:currentRoom,new:nr});currentRoom=nr;document.getElementById('roomName').innerText=currentRoom;document.querySelectorAll('.room-item').forEach(i=>i.classList.remove('active'));el.classList.add('active');msgDiv.innerHTML='<div class="system-msg">⏳ Загрузка...</div>';};});});
socket.on('users',l=>{let c=document.getElementById('usersList');c.innerHTML=l.map(u=>`<div class="user-item" onclick="showUser('${escape(u.name)}')"><span class="online-dot"></span> ${u.avatar||'👤'} ${escape(u.name)} ${u.role==='owner'?'<span class="badge-owner">ВЛ</span>':(u.role==='admin'?'<span class="badge-admin">АДМ</span>':'')}</div>`).join('');document.getElementById('onlineCount').innerHTML=`👥 ${l.length}`;});
socket.on('friends',l=>{let c=document.getElementById('friendsList');if(c)c.innerHTML=l.map(f=>`<div class="user-item" onclick="showUser('${escape(f.name)}')">👫 ${escape(f.name)}</div>`).join('');});
socket.on('typing',d=>{if(d.typing)typingUsers[d.name]=true;else delete typingUsers[d.name];let n=Object.keys(typingUsers).filter(n=>n!==username);document.getElementById('typingStatus').innerText=n.length?(n.length===1?`${n[0]} печатает...`:`${n.length} человек печатают...`):'';});
document.getElementById('sendBtn').onclick=()=>{let t=msgInput.value.trim();if(t){if(t.startsWith('/giveadmin ')&&role==='owner'){let target=t.split(' ')[1];fetch('/give_admin',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:target})}).then(r=>r.json()).then(data=>addSystem(data.message));msgInput.value='';return;}if(t.startsWith('/unadmin ')&&role==='owner'){let target=t.split(' ')[1];fetch('/remove_admin',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:target})}).then(r=>r.json()).then(data=>addSystem(data.message));msgInput.value='';return;}socket.emit('message',{text:t,room:currentRoom});msgInput.value='';}};
msgInput.onkeypress=e=>{if(e.key==='Enter')document.getElementById('sendBtn').click();socket.emit('typing',{room:currentRoom,typing:true});clearTimeout(window.tt);window.tt=setTimeout(()=>socket.emit('typing',{room:currentRoom,typing:false}),1000);};
document.getElementById('createRoomBtn')?.addEventListener('click',()=>{let n=document.getElementById('newRoom').value.trim();if(n){socket.emit('create',{room:n});document.getElementById('newRoom').value='';}});
document.getElementById('profileBtn').onclick=()=>document.getElementById('profileModal').style.display='flex';
document.getElementById('settingsBtn').onclick=()=>{document.getElementById('settingsModal').style.display='flex';loadRequests();};
document.getElementById('closeProfile').onclick=()=>document.getElementById('profileModal').style.display='none';
document.getElementById('closeSettings').onclick=()=>document.getElementById('settingsModal').style.display='none';
document.getElementById('closeUserModal').onclick=()=>document.getElementById('userModal').style.display='none';
document.getElementById('saveProfile').onclick=()=>{fetch('/update_profile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({avatar:document.getElementById('avatarInput').value,bio:document.getElementById('bioInput').value,new_name:document.getElementById('newName').value,new_password:document.getElementById('newPass').value})}).then(r=>r.json()).then(data=>{if(data.success){alert('Сохранено! Страница перезагрузится.');location.reload();}else alert('Ошибка: '+data.error);});};
document.getElementById('themeBtn').onclick=()=>{dark=!dark;if(dark)document.body.classList.add('dark');else document.body.classList.remove('dark');};
document.getElementById('logoutBtn').onclick=()=>window.location.href='/logout';
window.onclick=e=>{if(e.target===document.getElementById('profileModal'))document.getElementById('profileModal').style.display='none';if(e.target===document.getElementById('settingsModal'))document.getElementById('settingsModal').style.display='none';if(e.target===document.getElementById('userModal'))document.getElementById('userModal').style.display='none';};
socket.emit('get_rooms');socket.emit('get_users');
</script>
</body>
</html>
'''

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    u = users.get(session['username'])
    if not u or u.get('banned'):
        session.clear()
        return redirect(url_for('login'))
    return render_template_string(CHAT_HTML, username=session['username'], role=u['role'], avatar=u.get('avatar','👤'), bio=u.get('bio',''))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        name = request.form['username']
        pwd = request.form['password']
        h = hashlib.sha256(pwd.encode()).hexdigest()
        if name in users and users[name]['password'] == h:
            if users[name].get('banned'):
                return render_template_string(LOGIN_HTML, error='Заблокирован')
            session['username'] = name
            return redirect(url_for('index'))
        return render_template_string(LOGIN_HTML, error='Неверные данные')
    return render_template_string(LOGIN_HTML)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['username']
        pwd = request.form['password']
        if name in users:
            return render_template_string(REGISTER_HTML, error='Имя занято')
        if len(name) < 3 or len(name) > 20:
            return render_template_string(REGISTER_HTML, error='Имя 3-20')
        if len(pwd) < 4:
            return render_template_string(REGISTER_HTML, error='Пароль мин 4')
        users[name] = {'password': hashlib.sha256(pwd.encode()).hexdigest(), 'role': 'user', 'avatar': '👤', 'bio': '', 'friends': [], 'requests': [], 'banned': False, 'theme': 'light'}
        save_users(users)
        return redirect(url_for('login'))
    return render_template_string(REGISTER_HTML)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/save_theme', methods=['POST'])
def save_theme():
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
    if data.get('new_password') and len(data['new_password']) >= 4:
        users[session['username']]['password'] = hashlib.sha256(data['new_password'].encode()).hexdigest()
    save_users(users)
    return jsonify({'success': True})

@app.route('/give_admin', methods=['POST'])
def give_admin():
    if 'username' not in session or users[session['username']]['role'] != 'owner':
        return jsonify({'message': 'Только владелец'})
    target = request.json.get('username')
    if target in users and users[target]['role'] != 'owner' and users[target]['role'] != 'admin':
        users[target]['role'] = 'admin'
        save_users(users)
        socketio.emit('system', {'text': f'⭐ {target} назначен администратором!'}, broadcast=True)
        return jsonify({'message': f'{target} теперь админ'})
    return jsonify({'message': 'Не найден или уже админ'})

@app.route('/remove_admin', methods=['POST'])
def remove_admin():
    if 'username' not in session or users[session['username']]['role'] != 'owner':
        return jsonify({'message': 'Только владелец'})
    target = request.json.get('username')
    if target in users and users[target]['role'] == 'admin':
        users[target]['role'] = 'user'
        save_users(users)
        socketio.emit('system', {'text': f'🔻 У {target} снята роль администратора'}, broadcast=True)
        return jsonify({'message': f'У {target} снята админка'})
    return jsonify({'message': 'Не найден или не админ'})

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
    socketio.emit('friend_request', {'from': name}, to=target)
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
    return jsonify({'requests': users[session['username']].get('requests', [])})

@app.route('/user_info/<name>')
def user_info(name):
    if name not in users:
        return jsonify({'error': 'Not found'}), 404
    u = users[name]
    is_friend = name in users.get(session.get('username', ''), {}).get('friends', []) if session.get('username') else False
    role_display = {'owner': 'Владелец', 'admin': 'Админ', 'user': 'Пользователь'}.get(u['role'], 'Пользователь')
    return jsonify({'username': name, 'bio': u.get('bio', ''), 'role_display': role_display, 'user_role': u['role'], 'avatar': u.get('avatar', '👤'), 'friends_count': len(u.get('friends', [])), 'is_friend': is_friend})

@socketio.on('join')
def on_join(data):
    username = session.get('username')
    if not username or users.get(username, {}).get('banned'):
        return
    room = data['room']
    join_room(room)
    emit('history', messages.get(room, []), to=request.sid)

@socketio.on('message')
def on_message(data):
    username = session.get('username')
    if not username or users.get(username, {}).get('banned'):
        return
    room = data['room']
    text = data['text']
    msg = {'id': str(datetime.now().timestamp()), 'name': username, 'text': text, 'time': datetime.now().strftime('%H:%M:%S'), 'avatar': users[username].get('avatar', '👤')}
    if room not in messages:
        messages[room] = []
    messages[room].append(msg)
    if len(messages[room]) > 100:
        messages[room] = messages[room][-100:]
    save_messages(messages)
    emit('message', msg, to=room, broadcast=True)

@socketio.on('switch')
def on_switch(data):
    username = session.get('username')
    if not username:
        return
    old = data['old']
    new = data['new']
    leave_room(old)
    join_room(new)
    emit('history', messages.get(new, []), to=request.sid)

@socketio.on('create')
def on_create(data):
    username = session.get('username')
    if not username or users[username]['role'] not in ['owner', 'admin']:
        return
    new_room = data['room'].strip()
    if new_room and new_room not in rooms:
        rooms.append(new_room)
        messages[new_room] = []
        save_rooms(rooms)
        save_messages(messages)
        emit('rooms', rooms, broadcast=True)

@socketio.on('typing')
def on_typing(data):
    username = session.get('username')
    if not username:
        return
    emit('typing', {'name': username, 'typing': data['typing']}, to=data['room'], broadcast=True, include_self=False)

@socketio.on('get_rooms')
def get_rooms():
    emit('rooms', rooms)

@socketio.on('get_users')
def get_users():
    users_list = []
    for name, u in users.items():
        if not u.get('banned'):
            users_list.append({'name': name, 'role': u['role'], 'avatar': u.get('avatar', '👤')})
    emit('users', users_list, broadcast=True)
    if session.get('username'):
        name = session['username']
        friends = [{'name': f} for f in users[name].get('friends', [])]
        emit('friends', friends, to=request.sid)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
