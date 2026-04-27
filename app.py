from flask import Flask, render_template_string, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime, timedelta
import os
import json
import hashlib
import random

DB_PATH = 'db'
os.makedirs(DB_PATH, exist_ok=True)

USERS_FILE = os.path.join(DB_PATH, 'users.json')
MESSAGES_FILE = os.path.join(DB_PATH, 'messages.json')
ROOMS_FILE = os.path.join(DB_PATH, 'rooms.json')
DMS_FILE = os.path.join(DB_PATH, 'dms.json')

app = Flask(__name__)
app.secret_key = 'secret-key-2024'
socketio = SocketIO(app, cors_allowed_origins="*")

def generate_short_id():
    return str(random.randint(1000, 99999999))

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
            'banned': False,
            'theme': 'light',
            'user_id': generate_short_id(),
            'id_change_count': 0,
            'last_id_change': None,
            'muted_until': None
        },
        'dimooon': {
            'password': hashlib.sha256('1111'.encode()).hexdigest(),
            'role': 'admin',
            'avatar': '😎',
            'bio': 'Админ',
            'friends': [],
            'requests': [],
            'banned': False,
            'theme': 'light',
            'user_id': generate_short_id(),
            'id_change_count': 0,
            'last_id_change': None,
            'muted_until': None
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
dms = load_dms()

LOGIN_HTML = '<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes"><title>Чатик</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}.card{background:rgba(255,255,255,0.95);border-radius:48px;padding:40px;max-width:400px;width:100%;text-align:center;box-shadow:0 25px 50px -12px rgba(0,0,0,0.25)}h1{margin-bottom:8px;background:linear-gradient(135deg,#667eea,#764ba2);-webkit-background-clip:text;-webkit-text-fill-color:transparent}.subtitle{color:#6b7280;margin-bottom:32px}input{width:100%;padding:16px;border:2px solid #e5e7eb;border-radius:32px;margin-bottom:16px;outline:none}input:focus{border-color:#667eea}button{width:100%;padding:16px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border:none;border-radius:32px;cursor:pointer}.error{background:#fee2e2;color:#dc2626;padding:12px;border-radius:24px;margin-bottom:20px}.footer{margin-top:24px}a{color:#667eea}</style></head><body><div class="card"><h1>💬 Чатик</h1><div class="subtitle">Общайся с друзьями</div>{% if error %}<div class="error">{{ error }}</div>{% endif %}<form method="post"><input type="text" name="username" placeholder="Имя" required autofocus><input type="password" name="password" placeholder="Пароль" required><button type="submit">Войти</button></form><div class="footer">Нет аккаунта? <a href="/register">Регистрация</a></div></div></body></html>'

REGISTER_HTML = '<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes"><title>Регистрация</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}.card{background:rgba(255,255,255,0.95);border-radius:48px;padding:40px;max-width:400px;width:100%;text-align:center;box-shadow:0 25px 50px -12px rgba(0,0,0,0.25)}h1{margin-bottom:32px;background:linear-gradient(135deg,#667eea,#764ba2);-webkit-background-clip:text;-webkit-text-fill-color:transparent}input{width:100%;padding:16px;border:2px solid #e5e7eb;border-radius:32px;margin-bottom:16px;outline:none}input:focus{border-color:#667eea}button{width:100%;padding:16px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border:none;border-radius:32px;cursor:pointer}.error{background:#fee2e2;color:#dc2626;padding:12px;border-radius:24px;margin-bottom:20px}.footer{margin-top:24px}a{color:#667eea}</style></head><body><div class="card"><h1>📝 Регистрация</h1>{% if error %}<div class="error">{{ error }}</div>{% endif %}<form method="post"><input type="text" name="username" placeholder="Имя (3-20)" required autofocus><input type="password" name="password" placeholder="Пароль (мин 4)" required><button type="submit">Создать</button></form><div class="footer">Уже есть? <a href="/login">Войти</a></div></div></body></html>'

CHAT_HTML = '''<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes"><title>Чатик</title><script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script><style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:linear-gradient(135deg,#1e1b4b,#4c1d95);height:100vh;display:flex;overflow:hidden}.sidebar{width:280px;background:rgba(255,255,255,0.95);backdrop-filter:blur(10px);border-right:1px solid rgba(0,0,0,0.1);display:flex;flex-direction:column;overflow-y:auto}body.dark .sidebar{background:#1e293b;color:#fff}.user-card{text-align:center;padding:24px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;cursor:pointer;margin-bottom:16px}.user-avatar{font-size:56px}.user-name{font-size:18px;font-weight:700}.user-bio{font-size:11px;opacity:0.85;margin-top:5px}.user-id{font-size:9px;opacity:0.6;margin-top:3px}.section-title{font-weight:600;padding:16px 20px 8px 20px;color:#475569;font-size:12px;text-transform:uppercase}.room-item,.user-item{padding:12px 20px;margin:4px 12px;border-radius:16px;cursor:pointer;display:flex;align-items:center;gap:12px;transition:0.2s}.room-item:hover,.user-item:hover{background:rgba(0,0,0,0.05)}.room-item.active{background:#4f46e5;color:#fff}.add-room{display:flex;gap:8px;margin:12px}.add-room input{flex:1;padding:10px;border-radius:40px;border:1px solid #ddd;outline:none}.add-room button{background:#4f46e5;color:#fff;border:none;border-radius:40px;padding:8px 20px;cursor:pointer}.chat-area{flex:1;display:flex;flex-direction:column;background:#fff}.chat-header{padding:16px 24px;background:#fff;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center}.messages{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:12px}.message{display:flex;gap:12px;align-items:flex-start;animation:fadeIn 0.2s}.message-own{justify-content:flex-end}@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}.message-avatar{width:40px;height:40px;background:#4f46e5;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:18px;cursor:pointer;flex-shrink:0}.message-content{background:#f1f5f9;padding:10px 16px;border-radius:20px;max-width:65%;word-break:break-word}.message-own .message-content{background:#4f46e5;color:#fff}.message-name{font-weight:700;font-size:13px;display:flex;align-items:center;gap:6px}.message-time{font-size:9px;opacity:0.6;margin-left:6px}.message-text{margin-top:4px;font-size:14px;line-height:1.4}.badge-owner{background:#ef4444;font-size:8px;padding:2px 6px;border-radius:20px}.badge-admin{background:#10b981;font-size:8px;padding:2px 6px;border-radius:20px}.online-dot{width:8px;height:8px;background:#10b981;border-radius:50%;display:inline-block;margin-right:8px}.system-msg{text-align:center;font-size:11px;color:#64748b;padding:6px;margin:4px 0}.typing{padding:6px 24px;font-size:11px;color:#64748b;font-style:italic}.input-area{display:flex;gap:12px;padding:16px 24px;background:#fff;border-top:1px solid #eee}.input-area input{flex:1;padding:14px 20px;border:2px solid #e2e8f0;border-radius:40px;outline:none;font-size:14px}.input-area button{background:#4f46e5;border:none;border-radius:50%;width:48px;height:48px;color:#fff;cursor:pointer;font-size:18px;display:flex;align-items:center;justify-content:center}.btn-settings,.btn-logout{margin:8px 12px;padding:12px;border-radius:20px;cursor:pointer;border:none;font-weight:500}.btn-settings{background:#e0e7ff;color:#4f46e5}.btn-logout{background:#fee2e2;color:#dc2626}.modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);align-items:center;justify-content:center;z-index:1000}.modal-content{background:#fff;border-radius:28px;padding:24px;max-width:400px;width:90%}.modal-content input,.modal-content textarea,.modal-content select{width:100%;padding:12px;margin:8px 0;border-radius:24px;border:1px solid #ddd;outline:none}.modal-content button{background:#4f46e5;color:#fff;border:none;padding:12px;border-radius:24px;width:100%;cursor:pointer;margin-top:8px}.close{float:right;font-size:24px;cursor:pointer}.emoji-picker{position:absolute;bottom:90px;left:20px;background:#fff;border-radius:20px;padding:12px;display:none;grid-template-columns:repeat(6,1fr);gap:8px;box-shadow:0 10px 25px rgba(0,0,0,0.15);z-index:1000}.emoji{font-size:28px;cursor:pointer;text-align:center;padding:6px;border-radius:12px}.notify-btn{position:relative;background:none;border:none;cursor:pointer;font-size:20px;padding:8px;border-radius:50%}.notify-badge{position:absolute;top:-2px;right:-2px;background:#ef4444;color:#fff;font-size:10px;min-width:18px;height:18px;border-radius:20px;display:none;align-items:center;justify-content:center}.friend-request-item{display:flex;justify-content:space-between;align-items:center;padding:12px;margin:8px 0;background:#f1f5f9;border-radius:20px}.profile-avatar{font-size:64px;text-align:center;margin-bottom:12px}.profile-name{font-size:20px;font-weight:700;text-align:center;margin-bottom:4px}.profile-role{text-align:center;font-size:12px;color:#6b7280;margin-bottom:8px}.profile-id{text-align:center;font-size:11px;color:#94a3b8;margin-bottom:16px;font-family:monospace;cursor:pointer}.profile-bio{background:#f1f5f9;padding:12px;border-radius:20px;margin:16px 0;font-size:14px}.profile-actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:16px}.profile-actions button{flex:1;padding:10px;border-radius:24px;border:none;cursor:pointer;font-weight:500}.dm-list{max-height:200px;overflow-y:auto}.toast{position:fixed;bottom:20px;right:20px;background:#4f46e5;color:#fff;padding:12px 20px;border-radius:40px;z-index:2000;animation:slideIn 0.3s;box-shadow:0 5px 15px rgba(0,0,0,0.2)}@keyframes slideIn{from{transform:translateX(100%);opacity:0}to{transform:translateX(0);opacity:1}}@media(max-width:680px){.sidebar{width:240px}.message-content{max-width:75%}}
</style>
</head>
<body>
<div class="sidebar">
    <div class="user-card" id="profileBtn">
        <div class="user-avatar">{{ avatar }}</div>
        <div class="user-name">{{ username }}{% if role == "owner" %}<span class="badge-owner"> ВЛ</span>{% elif role == "admin" %}<span class="badge-admin"> АДМ</span>{% endif %}</div>
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
        <span id="roomName">Главная</span>
        <button class="notify-btn" id="notifyBtn"><span class="notify-badge" id="notifyBadge">0</span>🔔</button>
    </div>
    <div id="messagesList" class="messages"></div>
    <div id="typingStatus" class="typing"></div>
    <div class="input-area">
        <button id="emojiBtn">😊</button>
        <input type="text" id="messageInput" placeholder="Сообщение...">
        <button id="sendBtn">📤</button>
    </div>
</div>

<div id="emojiPicker" class="emoji-picker"></div>
<div id="profileModal" class="modal"><div class="modal-content"><span class="close" id="closeProfile">&times;</span><h3>👤 Мой профиль</h3><label>Аватар:</label><input type="text" id="avatarInput" maxlength="2" placeholder="😀"><label>О себе:</label><textarea id="bioInput" rows="3">{{ bio }}</textarea><label>Новое имя:</label><input type="text" id="newName"><label>Новый пароль:</label><input type="password" id="newPass"><div id="idChangeInfo"></div><button id="changeIdBtn">🆔 Сменить ID</button><button id="saveProfile">💾 Сохранить</button></div></div>
<div id="settingsModal" class="modal"><div class="modal-content"><span class="close" id="closeSettings">&times;</span><h3>⚙️ Настройки</h3><button id="themeBtn">🌙 Тёмная тема</button></div></div>
<div id="notifyModal" class="modal"><div class="modal-content"><span class="close" id="closeNotifyModal">&times;</span><h3>🔔 Уведомления</h3><div id="notificationsList"></div></div></div>
<div id="userModal" class="modal"><div class="modal-content"><span class="close" id="closeUserModal">&times;</span><div id="userModalContent"></div></div></div>
<div id="dmModal" class="modal"><div class="modal-content"><span class="close" id="closeDmModal">&times;</span><h3>💬 Личный чат с <span id="dmTargetName"></span></h3><div id="dmMessages" style="height:300px;overflow-y:auto;background:#f1f5f9;padding:12px;border-radius:20px;margin:12px 0"></div><div style="display:flex;gap:8px"><input type="text" id="dmInput" placeholder="Сообщение..." style="flex:1;padding:12px;border-radius:20px;border:1px solid #ddd"><button id="dmSendBtn" style="background:#4f46e5;color:#fff;border:none;border-radius:20px;padding:10px 20px">📤</button></div></div></div>

<script>
let socket=io(),currentRoom='Главная',username='{{ username }}',role='{{ role }}',user_id='{{ user_id }}',typingUsers={};
let notifications=[],pendingFriendRequests=[],currentDMTarget=null;
const msgDiv=document.getElementById('messagesList'),msgInput=document.getElementById('messageInput');

function showToast(msg,type='success'){
    let t=document.createElement('div');t.className='toast';t.style.background=type==='success'?'#10b981':(type==='error'?'#ef4444':'#4f46e5');t.innerHTML=msg;document.body.appendChild(t);setTimeout(()=>t.remove(),3000);
}

// Тёмная тема
const savedTheme = localStorage.getItem('chatTheme');
if(savedTheme === 'dark'){document.body.classList.add('dark');}
document.getElementById('themeBtn').onclick=()=>{
    document.body.classList.toggle('dark');
    localStorage.setItem('chatTheme',document.body.classList.contains('dark')?'dark':'light');
};

function addNotification(title,text){notifications.unshift({title,text,time:new Date().toLocaleTimeString()});if(notifications.length>20)notifications.pop();updateBadge();updateNotifList();}
function updateBadge(){let b=document.getElementById('notifyBadge');let c=notifications.length+pendingFriendRequests.length;if(c>0){b.textContent=c>99?'99+':c;b.style.display='flex';}else b.style.display='none';}
function updateNotifList(){let c=document.getElementById('notificationsList');if(notifications.length===0&&pendingFriendRequests.length===0){c.innerHTML='<p style="color:#6b7280;text-align:center;padding:16px">Нет уведомлений</p>';return;}let h='';pendingFriendRequests.forEach(r=>{h+=`<div class="friend-request-item"><span>📨 Заявка от ${escape(r)}</span><button onclick="acceptReq('${escape(r)}')" style="background:#10b981;border:none;border-radius:20px;padding:6px 14px;color:#fff;cursor:pointer">Принять</button></div>`;});notifications.forEach(n=>{h+=`<div class="friend-request-item"><div><strong>${escape(n.title)}</strong><br><small>${escape(n.text)}</small><br><span style="font-size:10px">${n.time}</span></div></div>`;});c.innerHTML=h;}
function loadRequests(){fetch('/get_requests').then(r=>r.json()).then(data=>{pendingFriendRequests=data.requests||[];updateBadge();updateNotifList();});}
document.getElementById('notifyBtn').onclick=()=>{document.getElementById('notifyModal').style.display='flex';updateNotifList();};
document.getElementById('closeNotifyModal').onclick=()=>document.getElementById('notifyModal').style.display='none';

fetch('/id_change_info').then(r=>r.json()).then(data=>{let d=document.getElementById('idChangeInfo');if(data.can_change)d.innerHTML='<p style="color:#10b981;margin:8px 0">✅ Можно сменить ID</p>';else d.innerHTML=`<p style="color:#f59e0b;margin:8px 0">⚠️ Следующая смена ID ${data.next_change_date}</p>`;});
document.getElementById('changeIdBtn').onclick=()=>{let nid=prompt('Новый ID (4-8 цифр):');if(nid&&/^\\d{4,8}$/.test(nid)){fetch('/change_id',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({new_id:nid})}).then(r=>r.json()).then(data=>{if(data.success){showToast('✅ ID изменён!','success');setTimeout(()=>location.reload(),1500);}else showToast('❌ '+data.error,'error');});}else showToast('❌ 4-8 цифр','error');};

function loadDMList(){fetch('/get_dm_list').then(r=>r.json()).then(data=>{let c=document.getElementById('dmList');if(data.dms&&data.dms.length){c.innerHTML=data.dms.map(d=>`<div class="user-item" onclick="openDM('${escape(d.with)}')"><span>💬 ${escape(d.with)}</span><span style="font-size:10px;color:#94a3b8">${escape(d.last_preview)}</span></div>`).join('');}else c.innerHTML='<div class="user-item" style="color:#94a3b8">Нет диалогов</div>';});}
function openDM(t){currentDMTarget=t;document.getElementById('dmTargetName').innerText=t;fetch('/get_dm/'+encodeURIComponent(t)).then(r=>r.json()).then(data=>{let c=document.getElementById('dmMessages');c.innerHTML=data.messages.map(m=>`<div style="margin:8px 0;text-align:${m.from===username?'right':'left'}"><div style="display:inline-block;background:${m.from===username?'#4f46e5':'#e2e8f0'};color:${m.from===username?'#fff':'#1f2937'};padding:8px 12px;border-radius:20px;max-width:80%"><strong>${escape(m.from)}</strong> (${m.time})<br>${escape(m.text)}</div></div>`).join('');c.scrollTop=c.scrollHeight;});document.getElementById('dmModal').style.display='flex';}
document.getElementById('closeDmModal').onclick=()=>document.getElementById('dmModal').style.display='none';
document.getElementById('dmSendBtn').onclick=()=>{let txt=document.getElementById('dmInput').value.trim();if(txt&&currentDMTarget){socket.emit('private_message',{target:currentDMTarget,text:txt});document.getElementById('dmInput').value='';}};
socket.on('private_message',(data)=>{if(data.from===currentDMTarget||data.to===currentDMTarget){let c=document.getElementById('dmMessages');let d=document.createElement('div');d.style=`margin:8px 0;text-align:${data.from===username?'right':'left'}`;d.innerHTML=`<div style="display:inline-block;background:${data.from===username?'#4f46e5':'#e2e8f0'};color:${data.from===username?'#fff':'#1f2937'};padding:8px 12px;border-radius:20px;max-width:80%"><strong>${escape(data.from)}</strong> (${data.time})<br>${escape(data.text)}</div>`;c.appendChild(d);c.scrollTop=c.scrollHeight;}addNotification('Личное сообщение',`${data.from}: ${data.text.substring(0,30)}`);loadDMList();});

const emojis=['😀','😂','❤️','👍','🎉','🔥','😍','🥹','😭','🤔','👋','🙏','✨','💯','😎','🥳'];
const picker=document.getElementById('emojiPicker');picker.innerHTML=emojis.map(e=>`<div class="emoji">${e}</div>`).join('');
document.querySelectorAll('.emoji').forEach(el=>el.onclick=()=>{msgInput.value+=el.textContent;msgInput.focus();picker.style.display='none';});
document.getElementById('emojiBtn').onclick=(e)=>{e.stopPropagation();picker.style.display=picker.style.display==='grid'?'none':'grid';};
document.addEventListener('click',(e)=>{if(!e.target.closest('#emojiBtn')&&!e.target.closest('.emoji-picker'))picker.style.display='none';});

function showUserProfile(name){
    fetch('/user_info/'+encodeURIComponent(name)).then(r=>r.json()).then(data=>{
        let actions=`<button onclick="openDM('${name}')" style="background:#8b5cf6;color:#fff">💬 Личка</button>`;
        if(!data.is_friend&&name!==username)actions+=`<button onclick="addFriend('${name}')" style="background:#10b981;color:#fff">➕ В друзья</button>`;
        if(data.is_friend)actions+=`<button onclick="removeFriend('${name}')" style="background:#ef4444;color:#fff">❌ Удалить</button>`;
        if(role==='owner'){
            if(data.user_role==='admin')actions+=`<button onclick="unadminUser('${name}')" style="background:#f59e0b;color:#fff">🔻 Снять админку</button>`;
            else if(data.user_role!=='owner')actions+=`<button onclick="giveAdmin('${name}')" style="background:#10b981;color:#fff">⭐ Выдать админку</button>`;
        }
        if(role==='owner'||role==='admin'){
            if(data.muted)actions+=`<button onclick="unmuteUser('${name}')" style="background:#10b981;color:#fff">🔊 Размутить</button>`;
            else actions+=`<select id="muteTime" style="width:100%;padding:8px;border-radius:20px;margin-bottom:8px"><option value="5">5 мин</option><option value="30">30 мин</option><option value="60">1 час</option><option value="1440">1 день</option><option value="10080">1 нед</option></select><button onclick="muteUser('${name}')" style="background:#f59e0b;color:#fff">🔇 Замутить</button>`;
            if(data.banned)actions+=`<button onclick="unbanUser('${name}')" style="background:#10b981;color:#fff">🔓 Разбанить</button>`;
            else actions+=`<button onclick="banUser('${name}')" style="background:#ef4444;color:#fff">🔨 Забанить</button>`;
        }
        document.getElementById('userModalContent').innerHTML=`
            <div class="profile-avatar">${data.avatar||'👤'}</div>
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
window.addFriend=name=>{fetch('/add_friend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({friend:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);showToast(data.message,'success');addNotification('Заявка',name);document.getElementById('userModal').style.display='none';});};
window.removeFriend=name=>{fetch('/remove_friend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({friend:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);showToast(data.message,'info');addNotification('Друг удалён',name);document.getElementById('userModal').style.display='none';});};
window.giveAdmin=name=>{fetch('/give_admin',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);showToast(data.message,'success');addNotification('Админ',`${name} назначен`);document.getElementById('userModal').style.display='none';});};
window.unadminUser=name=>{fetch('/remove_admin',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);showToast(data.message,'warning');addNotification('Админ',`У ${name} снято`);document.getElementById('userModal').style.display='none';});};
window.acceptReq=name=>{fetch('/accept_friend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({friend:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);showToast(data.message,'success');addNotification('Новый друг',name);pendingFriendRequests=pendingFriendRequests.filter(r=>r!==name);updateBadge();updateNotifList();loadRequests();});};
function addSystem(t){let d=document.createElement('div');d.className='system-msg';d.textContent=t;msgDiv.appendChild(d);msgDiv.scrollTop=msgDiv.scrollHeight;}
function addMessage(id,name,text,time,isOwn,avatar){let div=document.createElement('div');div.className=`message ${isOwn?'message-own':''}`;let badge='';if(name==='MrAizex')badge='<span class="badge-owner">ВЛ</span>';else if(name==='dimooon')badge='<span class="badge-admin">АДМ</span>';div.innerHTML=`<div class="message-avatar" onclick="showUserProfile('${escape(name)}')">${avatar||'👤'}</div><div class="message-content"><div class="message-name">${escape(name)}${badge}<span class="message-time">${time}</span></div><div class="message-text">${escape(text)}</div></div>`;msgDiv.appendChild(div);msgDiv.scrollTop=msgDiv.scrollHeight;}
function escape(s){return s.replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'})[m]);}
socket.emit('join',{room:currentRoom});
socket.on('history',h=>{msgDiv.innerHTML='';h.forEach(m=>addMessage(m.id,m.name,m.text,m.time,m.name===username,m.avatar));});
socket.on('message',m=>addMessage(m.id,m.name,m.text,m.time,m.name===username,m.avatar));
socket.on('system',d=>addSystem(d.text));
socket.on('friend_request',data=>{addNotification('Заявка',`${data.from} хочет добавить вас`);loadRequests();});
socket.on('rooms',l=>{let c=document.getElementById('roomsList');c.innerHTML=l.map(r=>`<div class="room-item ${r===currentRoom?'active':''}" data-room="${r}">🏠 ${escape(r)}</div>`).join('');document.querySelectorAll('.room-item').forEach(el=>{el.onclick=()=>{let nr=el.dataset.room;if(nr===currentRoom)return;socket.emit('switch',{old:currentRoom,new:nr});currentRoom=nr;document.getElementById('roomName').innerText=currentRoom;document.querySelectorAll('.room-item').forEach(i=>i.classList.remove('active'));el.classList.add('active');msgDiv.innerHTML='<div class="system-msg">⏳ Загрузка...</div>';};});});
socket.on('users',l=>{let c=document.getElementById('usersList');c.innerHTML=l.map(u=>`<div class="user-item" onclick="showUserProfile('${escape(u.name)}')"><span class="online-dot"></span> ${u.avatar||'👤'} ${escape(u.name)} ${u.role==='owner'?'<span class="badge-owner">ВЛ</span>':(u.role==='admin'?'<span class="badge-admin">АДМ</span>':'')}</div>`).join('');loadDMList();});
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
document.getElementById('saveProfile').onclick=()=>{fetch('/update_profile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({avatar:document.getElementById('avatarInput').value,bio:document.getElementById('bioInput').value,new_name:document.getElementById('newName').value,new_password:document.getElementById('newPass').value})}).then(r=>r.json()).then(data=>{if(data.success){showToast('✅ Профиль сохранён','success');setTimeout(()=>location.reload(),1000);}else showToast('❌ '+data.error,'error');});};
document.getElementById('logoutBtn').onclick=()=>window.location.href='/logout';
window.onclick=e=>{if(e.target===document.getElementById('profileModal'))document.getElementById('profileModal').style.display='none';if(e.target===document.getElementById('settingsModal'))document.getElementById('settingsModal').style.display='none';if(e.target===document.getElementById('notifyModal'))document.getElementById('notifyModal').style.display='none';if(e.target===document.getElementById('userModal'))document.getElementById('userModal').style.display='none';if(e.target===document.getElementById('dmModal'))document.getElementById('dmModal').style.display='none';};
loadRequests();socket.emit('get_rooms');socket.emit('get_users');
</script>
</body>
</html>'''

# ==== МАРШРУТЫ ====
@app.route('/')
def index():
    if 'username' not in session: return redirect(url_for('login'))
    u = users.get(session['username'])
    if not u or u.get('banned'): session.clear(); return redirect(url_for('login'))
    return render_template_string(CHAT_HTML, username=session['username'], role=u['role'], avatar=u.get('avatar','👤'), bio=u.get('bio',''), user_id=u.get('user_id',''))

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
        users[name] = {'password': hashlib.sha256(pwd.encode()).hexdigest(), 'role': 'user', 'avatar': '👤', 'bio': '', 'friends': [], 'requests': [], 'banned': False, 'theme': 'light', 'user_id': generate_short_id(), 'id_change_count': 0, 'last_id_change': None, 'muted_until': None}
        save_users(users); return redirect(url_for('login'))
    return render_template_string(REGISTER_HTML)

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/save_theme', methods=['POST'])
def save_theme():
    if 'username' in session: users[session['username']]['theme'] = request.json.get('theme', 'light'); save_users(users)
    return jsonify({'success': True})

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'username' not in session: return jsonify({'error': 'Not logged'}), 401
    name = session['username']; data = request.json
    if data.get('avatar'): users[name]['avatar'] = data['avatar'][:2]
    if data.get('bio') is not None: users[name]['bio'] = data['bio'][:200]
    if data.get('new_name'):
        nn = data['new_name']
        if len(nn)<3 or len(nn)>20: return jsonify({'error': 'Имя 3-20'}), 400
        if nn in users and nn != name: return jsonify({'error': 'Имя занято'}), 400
        users[nn] = users.pop(name); session['username'] = nn
    if data.get('new_password') and len(data['new_password'])>=4: users[session['username']]['password'] = hashlib.sha256(data['new_password'].encode()).hexdigest()
    save_users(users); return jsonify({'success': True})

@app.route('/change_id', methods=['POST'])
def change_id():
    if 'username' not in session: return jsonify({'error': 'Not logged'}), 401
    name = session['username']; new_id = request.json.get('new_id')
    if not new_id or not new_id.isdigit() or len(new_id)<4 or len(new_id)>8: return jsonify({'error': 'ID должен быть числом от 4 до 8 цифр'})
    u = users[name]
    if u.get('id_change_count',0)==0:
        u['user_id']=new_id; u['id_change_count']=1; u['last_id_change']=datetime.now().isoformat(); save_users(users); return jsonify({'success': True})
    else:
        last_change = datetime.fromisoformat(u['last_id_change']) if u.get('last_id_change') else None
        if last_change and datetime.now()-last_change<timedelta(days=14):
            next_change = last_change+timedelta(days=14)
            return jsonify({'error': f'Следующая смена ID с {next_change.strftime("%d.%m.%Y %H:%M")}'})
        u['user_id']=new_id; u['last_id_change']=datetime.now().isoformat(); save_users(users); return jsonify({'success': True})

@app.route('/id_change_info')
def id_change_info():
    if 'username' not in session: return jsonify({'can_change': False, 'next_change_date': ''})
    name = session['username']; u = users[name]
    if u.get('id_change_count',0)==0: return jsonify({'can_change': True, 'next_change_date': ''})
    last_change = datetime.fromisoformat(u['last_id_change']) if u.get('last_id_change') else None
    if last_change and datetime.now()-last_change<timedelta(days=14): next_change = last_change+timedelta(days=14); return jsonify({'can_change': False, 'next_change_date': next_change.strftime("%d.%m.%Y %H:%M")})
    return jsonify({'can_change': True, 'next_change_date': ''})

@app.route('/give_admin', methods=['POST'])
def give_admin():
    if 'username' not in session or users[session['username']]['role']!='owner': return jsonify({'message': 'Только владелец'})
    target = request.json.get('username')
    if target in users and users[target]['role']!='owner' and users[target]['role']!='admin':
        users[target]['role']='admin'; save_users(users); socketio.emit('system',{'text':f'⭐ {target} назначен администратором!'}, broadcast=True); return jsonify({'message': f'{target} теперь админ'})
    return jsonify({'message': 'Не найден или уже админ'})

@app.route('/remove_admin', methods=['POST'])
def remove_admin():
    if 'username' not in session or users[session['username']]['role']!='owner': return jsonify({'message': 'Только владелец'})
    target = request.json.get('username')
    if target in users and users[target]['role']=='admin':
        users[target]['role']='user'; save_users(users); socketio.emit('system',{'text':f'🔻 У {target} снята админка'}, broadcast=True); return jsonify({'message': f'У {target} снята админка'})
    return jsonify({'message': 'Не найден или не админ'})

@app.route('/mute_user', methods=['POST'])
def mute_user():
    if 'username' not in session or users[session['username']]['role'] not in ['owner','admin']: return jsonify({'message': 'Нет прав'})
    target = request.json.get('username'); minutes = int(request.json.get('minutes',5))
    if target not in users or users[target]['role']=='owner': return jsonify({'message': 'Нельзя замутить владельца'})
    users[target]['muted_until'] = (datetime.now()+timedelta(minutes=minutes)).isoformat(); save_users(users)
    socketio.emit('system',{'text':f'🔇 {target} замучен на {minutes} минут'}, broadcast=True)
    return jsonify({'message': f'{target} замучен на {minutes} минут'})

@app.route('/unmute_user', methods=['POST'])
def unmute_user():
    if 'username' not in session or users[session['username']]['role'] not in ['owner','admin']: return jsonify({'message': 'Нет прав'})
    target = request.json.get('username')
    if target not in users: return jsonify({'message': 'Не найден'})
    users[target]['muted_until'] = None; save_users(users)
    socketio.emit('system',{'text':f'🔊 {target} размучен!'}, broadcast=True)
    return jsonify({'message': f'{target} размучен'})

@app.route('/ban_user', methods=['POST'])
def ban_user():
    if 'username' not in session or users[session['username']]['role'] not in ['owner','admin']: return jsonify({'message': 'Нет прав'})
    target = request.json.get('username')
    if target not in users or users[target]['role']=='owner': return jsonify({'message': 'Нельзя забанить владельца'})
    users[target]['banned'] = True; save_users(users)
    socketio.emit('system',{'text':f'🔨 {target} забанен!'}, broadcast=True)
    return jsonify({'message': f'{target} забанен'})

@app.route('/unban_user', methods=['POST'])
def unban_user():
    if 'username' not in session or users[session['username']]['role'] not in ['owner','admin']: return jsonify({'message': 'Нет прав'})
    target = request.json.get('username')
    if target in users:
        users[target]['banned'] = False; save_users(users)
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
    users[target]['requests'].append(name); save_users(users); socketio.emit('friend_request',{'from':name}, to=target)
    return jsonify({'message': f'Заявка отправлена {target}'})

@app.route('/accept_friend', methods=['POST'])
def accept_friend():
    if 'username' not in session: return jsonify({'message': 'Войдите'})
    name = session['username']; target = request.json.get('friend')
    if target not in users[name]['requests']: return jsonify({'message': 'Нет заявки'})
    users[name]['requests'].remove(target); users[name]['friends'].append(target); users[target]['friends'].append(name); save_users(users)
    return jsonify({'message': f'Вы приняли заявку от {target}'})

@app.route('/remove_friend', methods=['POST'])
def remove_friend():
    if 'username' not in session: return jsonify({'message': 'Войдите'})
    name = session['username']; target = request.json.get('friend')
    if target in users[name]['friends']:
        users[name]['friends'].remove(target); users[target]['friends'].remove(name); save_users(users); return jsonify({'message': f'{target} удалён из друзей'})
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
    role_display = {'owner':'Владелец','admin':'Админ','user':'Пользователь'}.get(u['role'],'Пользователь')
    return jsonify({'username':name,'bio':u.get('bio',''),'role_display':role_display,'user_role':u['role'],'avatar':u.get('avatar','👤'),'user_id':u.get('user_id',''),'friends_count':len(u.get('friends',[])),'is_friend':is_friend,'banned':u.get('banned',False),'muted':u.get('muted_until') and datetime.now()<datetime.fromisoformat(u['muted_until'])})

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

@socketio.on('private_message')
def private_message(data):
    username = session.get('username')
    if not username: return
    target = data['target']; text = data['text']
    key = f"{min(username,target)}_{max(username,target)}"
    msg = {'from': username, 'to': target, 'text': text, 'time': datetime.now().strftime('%H:%M:%S')}
    if key not in dms: dms[key] = []
    dms[key].append(msg); save_dms(dms)
    emit('private_message', msg, to=target); emit('private_message', msg, to=username)

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
    if u.get('muted_until') and datetime.now()<datetime.fromisoformat(u['muted_until']):
        emit('system', {'text': '🔇 Вы замучены и не можете писать!'}, to=request.sid); return
    room = data['room']; text = data['text']
    msg = {'id': str(datetime.now().timestamp()), 'name': username, 'text': text, 'time': datetime.now().strftime('%H:%M:%S'), 'avatar': users[username].get('avatar','👤')}
    if room not in messages: messages[room] = []
    messages[room].append(msg)
    if len(messages[room])>100: messages[room] = messages[room][-100:]
    save_messages(messages); emit('message', msg, to=room, broadcast=True)

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
    if new_room and new_room not in rooms: rooms.append(new_room); messages[new_room] = []; save_rooms(rooms); save_messages(messages); emit('rooms', rooms, broadcast=True)

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
    for name,u in users.items():
        if not u.get('banned'): lst.append({'name': name, 'role': u['role'], 'avatar': u.get('avatar','👤')})
    emit('users', lst, broadcast=True)
    if session.get('username'):
        name = session['username']; friends = [{'name': f} for f in users[name].get('friends',[])]; emit('friends', friends, to=request.sid)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
