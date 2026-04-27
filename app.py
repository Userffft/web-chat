import os
import json
import hashlib
import random
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
app.secret_key = 'secret-key-2024'
socketio = SocketIO(app, cors_allowed_origins="*")

DB_PATH = 'db'
os.makedirs(DB_PATH, exist_ok=True)

USERS_FILE = os.path.join(DB_PATH, 'users.json')
MESSAGES_FILE = os.path.join(DB_PATH, 'messages.json')
ROOMS_FILE = os.path.join(DB_PATH, 'rooms.json')
FRIENDS_FILE = os.path.join(DB_PATH, 'friends.json')  # отдельно для упрощения
DMS_FILE = os.path.join(DB_PATH, 'dms.json')

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {
        'MrAizex': {'password': hashlib.sha256('admin123'.encode()).hexdigest(), 'role': 'owner', 'avatar': '👑', 'bio': 'Владелец', 'banned': False, 'muted_until': None, 'online': False},
        'dimooon': {'password': hashlib.sha256('1111'.encode()).hexdigest(), 'role': 'admin', 'avatar': '😎', 'bio': 'Админ', 'banned': False, 'muted_until': None, 'online': False}
    }

def save_users(u): json.dump(u, open(USERS_FILE, 'w'))

def load_messages():
    if os.path.exists(MESSAGES_FILE):
        with open(MESSAGES_FILE, 'r') as f:
            return json.load(f)
    return {'Главная': []}

def save_messages(m): json.dump(m, open(MESSAGES_FILE, 'w'))

def load_rooms():
    if os.path.exists(ROOMS_FILE):
        with open(ROOMS_FILE, 'r') as f:
            return json.load(f)
    return ['Главная']

def save_rooms(r): json.dump(r, open(ROOMS_FILE, 'w'))

def load_friends():
    if os.path.exists(FRIENDS_FILE):
        with open(FRIENDS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_friends(f): json.dump(f, open(FRIENDS_FILE, 'w'))

def load_dms():
    if os.path.exists(DMS_FILE):
        with open(DMS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_dms(d): json.dump(d, open(DMS_FILE, 'w'))

users = load_users()
messages = load_messages()
rooms = load_rooms()
friends = load_friends()
dms = load_dms()

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
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes"><title>Чатик · {{ username }}</title><script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script><style>
*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:linear-gradient(135deg,#1e1b4b,#4c1d95);height:100vh;display:flex}body.dark{background:#0f0f0f}.sidebar{width:260px;background:rgba(255,255,255,0.95);backdrop-filter:blur(10px);border-right:1px solid rgba(0,0,0,0.1);display:flex;flex-direction:column;overflow-y:auto}body.dark .sidebar{background:#1a1a1a;color:#fff}.user-card{text-align:center;padding:20px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;cursor:pointer;margin:12px;border-radius:24px}.user-avatar{font-size:48px}.user-name{font-size:16px;font-weight:700}.user-bio{font-size:11px;opacity:0.8;margin-top:5px}.section-title{font-weight:600;padding:12px 16px 4px 16px;color:#475569;font-size:11px;text-transform:uppercase}body.dark .section-title{color:#94a3b8}.room-item,.user-item{padding:10px 16px;margin:4px 12px;border-radius:16px;cursor:pointer;display:flex;align-items:center;gap:10px;transition:0.1s}.room-item:hover,.user-item:hover{background:rgba(0,0,0,0.05)}.room-item.active{background:#4f46e5;color:#fff}.add-room{display:flex;gap:6px;margin:12px}.add-room input{flex:1;padding:8px 12px;border-radius:40px;border:1px solid #ddd;outline:none}body.dark .add-room input{background:#333;color:#fff}.add-room button{background:#4f46e5;color:#fff;border:none;border-radius:40px;padding:6px 16px;cursor:pointer}.chat-area{flex:1;display:flex;flex-direction:column;background:#fff}body.dark .chat-area{background:#0a0a0a}.chat-header{padding:12px 20px;background:#fff;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center}body.dark .chat-header{background:#1a1a1a;color:#fff}.room-name{font-weight:600;cursor:pointer;padding:4px 8px;border-radius:20px}.room-name:hover{background:rgba(0,0,0,0.05)}.messages{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:8px}.message{display:flex;gap:10px;align-items:flex-start;animation:fadeIn 0.15s}.message-own{justify-content:flex-end}.message-avatar{width:36px;height:36px;background:#4f46e5;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:18px;cursor:pointer}.message-content{background:#f1f5f9;padding:8px 12px;border-radius:18px;max-width:65%;word-break:break-word}body.dark .message-content{background:#2a2a2a;color:#fff}.message-own .message-content{background:#4f46e5;color:#fff}.message-name{font-weight:600;font-size:12px;margin-bottom:2px}.message-time{font-size:9px;opacity:0.6;margin-left:6px}.badge-owner{background:#ef4444;padding:2px 6px;border-radius:20px;font-size:9px;margin-left:6px}.badge-admin{background:#10b981;padding:2px 6px;border-radius:20px;font-size:9px;margin-left:6px}.online-dot{width:8px;height:8px;background:#10b981;border-radius:50%;display:inline-block;margin-right:6px}.system-msg{text-align:center;font-size:11px;color:#64748b;padding:4px}.typing{padding:4px 20px;font-size:11px;color:#64748b;font-style:italic}.input-area{display:flex;gap:8px;padding:12px 20px;background:#fff;border-top:1px solid #eee}body.dark .input-area{background:#1a1a1a}.input-area input{flex:1;padding:10px 16px;border:2px solid #e2e8f0;border-radius:40px;outline:none;font-size:14px}body.dark .input-area input{background:#2a2a2a;color:#fff}.input-area button{background:#4f46e5;border:none;border-radius:50%;width:44px;height:44px;color:#fff;cursor:pointer;font-size:18px}.btn-settings,.btn-logout{margin:6px 12px;padding:10px;border-radius:20px;border:none;font-weight:500;cursor:pointer;transition:0.1s}.btn-settings{background:#e0e7ff;color:#4f46e5}body.dark .btn-settings{background:#2a2a2a;color:#818cf8}.btn-logout{background:#fee2e2;color:#dc2626}.modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);align-items:center;justify-content:center;z-index:1000}.modal-content{background:#fff;border-radius:24px;padding:24px;max-width:350px;width:90%}body.dark .modal-content{background:#1a1a1a}.modal-content input,.modal-content textarea{width:100%;padding:10px;margin:6px 0;border-radius:20px;border:1px solid #ddd}.modal-content button{background:#4f46e5;color:#fff;border:none;padding:10px;border-radius:20px;width:100%;cursor:pointer;margin-top:8px}.close{float:right;font-size:24px;cursor:pointer}.emoji-picker{position:absolute;bottom:80px;left:20px;background:#fff;border-radius:20px;padding:8px;display:none;grid-template-columns:repeat(6,1fr);gap:6px;box-shadow:0 5px 15px rgba(0,0,0,0.2);z-index:1000}.emoji{font-size:24px;cursor:pointer;text-align:center;padding:4px;border-radius:12px}.toast{position:fixed;bottom:20px;right:20px;background:#4f46e5;color:#fff;padding:10px 18px;border-radius:40px;z-index:2000;animation:slideIn 0.2s}@keyframes slideIn{from{transform:translateX(100%)}to{transform:translateX(0)}}.user-menu{position:fixed;background:#fff;border-radius:16px;box-shadow:0 5px 15px rgba(0,0,0,0.2);padding:6px;z-index:2000;display:none;min-width:160px}body.dark .user-menu{background:#1a1a1a}.user-menu button{width:100%;padding:8px 12px;border:none;background:none;text-align:left;cursor:pointer;border-radius:12px}.user-menu button:hover{background:#f1f5f9}@media(max-width:600px){.sidebar{width:220px}}
</style>
</head>
<body>
<div class="sidebar">
    <div class="user-card" id="profileBtn">
        <div class="user-avatar">{{ avatar }}</div>
        <div class="user-name">{{ username }}{% if role == "owner" %}<span class="badge-owner">ВЛ</span>{% elif role == "admin" %}<span class="badge-admin">АДМ</span>{% endif %}</div>
        <div class="user-bio">{{ bio[:30] }}</div>
    </div>
    <div class="section-title">🏠 КОМНАТЫ</div>
    <div id="roomsList"></div>
    {% if role in ["owner","admin"] %}<div class="add-room"><input type="text" id="newRoom" placeholder="Название"><button id="createRoomBtn">+</button></div>{% endif %}
    <div class="section-title">👥 ОНЛАЙН</div>
    <div id="usersList"></div>
    <div class="section-title">👫 ДРУЗЬЯ</div>
    <div id="friendsList"></div>
    <button class="btn-settings" id="settingsBtn">⚙️ Настройки</button>
    <button class="btn-logout" id="logoutBtn">🚪 Выйти</button>
</div>
<div class="chat-area">
    <div class="chat-header">
        <span class="room-name" id="roomName">Главная</span>
        <button class="notify-btn" id="notifyBtn" style="background:none;border:none;cursor:pointer;font-size:18px">🔔<span id="notifyBadge" style="display:none;background:red;color:white;border-radius:20px;padding:0 6px;margin-left:4px">0</span></button>
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
<div id="profileModal" class="modal"><div class="modal-content"><span class="close" id="closeProfile">&times;</span><h3>Мой профиль</h3><label>Аватар (эмодзи):</label><input type="text" id="avatarInput" maxlength="2" placeholder="😀"><label>О себе:</label><textarea id="bioInput" rows="3">{{ bio }}</textarea><label>Новое имя:</label><input type="text" id="newName"><label>Новый пароль:</label><input type="password" id="newPass"><div id="idChangeInfo"></div><button id="changeIdBtn">Сменить ID</button><button id="saveProfile">Сохранить</button></div></div>
<div id="settingsModal" class="modal"><div class="modal-content"><span class="close" id="closeSettings">&times;</span><h3>Настройки</h3><button id="themeBtn">Тёмная тема</button><button id="clearHistory">Очистить историю</button></div></div>
<div id="notifyModal" class="modal"><div class="modal-content"><span class="close" id="closeNotifyModal">&times;</span><h3>Уведомления</h3><div id="notificationsList"></div></div></div>
<div id="userModal" class="modal"><div class="modal-content"><span class="close" id="closeUserModal">&times;</span><div id="userModalContent"></div></div></div>
<div id="userMenu" class="user-menu"></div>
<script>
let socket=io(),currentRoom='Главная',username='{{ username }}',role='{{ role }}',typingUsers={};
let notifications=[],friendRequests=[],currentMenuUser=null;
const msgDiv=document.getElementById('messagesList'),msgInput=document.getElementById('messageInput');
function showToast(msg){let t=document.createElement('div');t.className='toast';t.innerHTML=msg;document.body.appendChild(t);setTimeout(()=>t.remove(),2000);}
const savedTheme=localStorage.getItem('chatTheme');if(savedTheme==='dark')document.body.classList.add('dark');
document.getElementById('themeBtn').onclick=()=>{document.body.classList.toggle('dark');localStorage.setItem('chatTheme',document.body.classList.contains('dark')?'dark':'light');};
document.getElementById('roomName').onclick=()=>{if(currentRoom!=='Главная'){socket.emit('switch',{old:currentRoom,new:'Главная'});currentRoom='Главная';document.getElementById('roomName').innerText='Главная';document.querySelectorAll('.room-item').forEach(i=>i.classList.remove('active'));let main=Array.from(document.querySelectorAll('.room-item')).find(el=>el.dataset.room==='Главная');if(main)main.classList.add('active');msgDiv.innerHTML='<div class="system-msg">Загрузка...</div>';}};
function addNotif(title,text){notifications.unshift({title,text,time:new Date().toLocaleTimeString()});if(notifications.length>20)notifications.pop();updateBadge();}
function updateBadge(){let b=document.getElementById('notifyBadge');let c=notifications.length+friendRequests.length;if(c>0){b.textContent=c>99?'99+':c;b.style.display='inline-block';}else b.style.display='none';}
function updateNotifList(){let c=document.getElementById('notificationsList');if(notifications.length===0&&friendRequests.length===0){c.innerHTML='<p>Нет уведомлений</p>';return;}let html='';friendRequests.forEach(r=>{html+=`<div style="padding:10px;margin:6px 0;background:#f1f5f9;border-radius:20px;display:flex;justify-content:space-between"><span>📨 Заявка от ${escape(r)}</span><button onclick="acceptReq('${escape(r)}')" style="background:#10b981;border:none;border-radius:20px;padding:4px 12px;color:#fff">Принять</button></div>`;});notifications.forEach(n=>{html+=`<div style="padding:10px;margin:6px 0;background:#f1f5f9;border-radius:20px"><strong>${escape(n.title)}</strong><br><small>${escape(n.text)}</small><br><span style="font-size:10px">${n.time}</span></div>`;});c.innerHTML=html;}
function loadRequests(){fetch('/get_friend_requests').then(r=>r.json()).then(data=>{friendRequests=data.requests||[];updateBadge();});}
document.getElementById('notifyBtn').onclick=()=>{document.getElementById('notifyModal').style.display='flex';updateNotifList();};
document.getElementById('closeNotifyModal').onclick=()=>document.getElementById('notifyModal').style.display='none';
fetch('/id_change_info').then(r=>r.json()).then(data=>{let d=document.getElementById('idChangeInfo');if(data.can_change)d.innerHTML='<p style="color:#10b981">✅ Можно сменить ID</p>';else d.innerHTML=`<p style="color:#f59e0b">⚠️ Следующая смена ID ${data.next_change_date}</p>`;});
document.getElementById('changeIdBtn').onclick=()=>{let nid=prompt('Новый ID (4-8 цифр):');if(nid&&/^\\d{4,8}$/.test(nid)){fetch('/change_id',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({new_id:nid})}).then(r=>r.json()).then(data=>{if(data.success){showToast('✅ ID изменён');setTimeout(()=>location.reload(),1500);}else showToast('❌ '+data.error);});}else showToast('ID 4-8 цифр');}};
document.getElementById('uploadAvatarBtn')?.addEventListener('click',()=>{let url=prompt('Введите URL аватара (или эмодзи)');if(url)document.getElementById('avatarInput').value=url;});
const emojis=['😀','😂','❤️','👍','🎉','🔥','😍','🥹','😭','🤔','👋','🙏','✨','💯','😎','🥳'];
const picker=document.getElementById('emojiPicker');picker.innerHTML=emojis.map(e=>`<div class="emoji">${e}</div>`).join('');
document.querySelectorAll('.emoji').forEach(el=>el.onclick=()=>{msgInput.value+=el.textContent;msgInput.focus();picker.style.display='none';});
document.getElementById('emojiBtn').onclick=(e)=>{e.stopPropagation();picker.style.display=picker.style.display==='grid'?'none':'grid';};
document.addEventListener('click',(e)=>{if(!e.target.closest('#emojiBtn')&&!e.target.closest('.emoji-picker'))picker.style.display='none';if(!e.target.closest('.user-item')&&!e.target.closest('.user-menu')&&!e.target.closest('.message-avatar')){document.getElementById('userMenu').style.display='none';currentMenuUser=null;}});
function showUserMenu(name,x,y){
    let menu=document.getElementById('userMenu');if(currentMenuUser===name&&menu.style.display==='block'){menu.style.display='none';currentMenuUser=null;return;}
    fetch('/user_info/'+encodeURIComponent(name)).then(r=>r.json()).then(data=>{
        let actions='';
        if(!data.is_friend)actions+=`<button onclick="addFriend('${name}')">➕ В друзья</button>`;
        if(data.is_friend)actions+=`<button onclick="removeFriend('${name}')">❌ Удалить из друзей</button>`;
        if(role==='owner'||role==='admin'){
            if(data.role==='admin')actions+=`<button onclick="unadmin('${name}')">🔻 Снять админку</button>`;
            else if(data.role!=='owner')actions+=`<button onclick="giveAdmin('${name}')">⭐ Выдать админку</button>`;
            if(data.muted)actions+=`<button onclick="unmute('${name}')">🔊 Размутить</button>`;
            else actions+=`<button onclick="muteUser('${name}')">🔇 Замутить</button>`;
            if(data.banned)actions+=`<button onclick="unban('${name}')">🔓 Разбанить</button>`;
            else actions+=`<button onclick="banUser('${name}')">🔨 Забанить</button>`;
        }
        menu.innerHTML=actions;menu.style.display='block';menu.style.left=x+'px';menu.style.top=y+'px';currentMenuUser=name;
        setTimeout(()=>{if(menu.style.display==='block'){menu.style.display='none';currentMenuUser=null;}},4000);
    });
}
window.giveAdmin=name=>fetch('/give_admin',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);showToast(data.message);document.getElementById('userMenu').style.display='none';});
window.unadmin=name=>fetch('/remove_admin',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);showToast(data.message);document.getElementById('userMenu').style.display='none';});
window.muteUser=name=>{let minutes=prompt('Минуты мута (5,30,60,1440,10080)','5');if(minutes) fetch('/mute_user',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:name,minutes:parseInt(minutes)})}).then(r=>r.json()).then(data=>{addSystem(data.message);showToast(data.message);document.getElementById('userMenu').style.display='none';});};
window.unmute=name=>fetch('/unmute_user',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);showToast(data.message);document.getElementById('userMenu').style.display='none';});
window.banUser=name=>fetch('/ban_user',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);showToast(data.message);document.getElementById('userMenu').style.display='none';});
window.unban=name=>fetch('/unban_user',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);showToast(data.message);document.getElementById('userMenu').style.display='none';});
window.addFriend=name=>fetch('/add_friend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({friend:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);showToast(data.message);document.getElementById('userMenu').style.display='none';loadRequests();});
window.removeFriend=name=>fetch('/remove_friend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({friend:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);showToast(data.message);document.getElementById('userMenu').style.display='none';});
window.acceptReq=name=>fetch('/accept_friend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({friend:name})}).then(r=>r.json()).then(data=>{addSystem(data.message);showToast('✅ Вы приняли заявку');friendRequests=friendRequests.filter(r=>r!==name);updateBadge();updateNotifList();loadRequests();});
function addSystem(t){let d=document.createElement('div');d.className='system-msg';d.textContent=t;msgDiv.appendChild(d);msgDiv.scrollTop=msgDiv.scrollHeight;}
function addMessage(id,name,text,time,isOwn,avatar){
    let div=document.createElement('div');div.className=`message ${isOwn?'message-own':''}`;let badge='';if(name==='MrAizex')badge='<span class="badge-owner">ВЛ</span>';else if(name==='dimooon')badge='<span class="badge-admin">АДМ</span>';
    div.innerHTML=`<div class="message-avatar" onclick="showUserMenu('${escape(name)}', event.clientX, event.clientY)">${avatar||'👤'}</div><div class="message-content"><div class="message-name">${escape(name)}${badge}<span class="message-time">${time}</span></div><div class="message-text">${escape(text)}</div></div>`;
    msgDiv.appendChild(div);msgDiv.scrollTop=msgDiv.scrollHeight;
}
function deleteMessage(msgId){fetch('/delete_message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messageId:msgId,room:currentRoom})}).then(()=>{document.querySelector(`.message[data-id="${msgId}"]`)?.remove();showToast('Сообщение удалено');});}
function escape(s){return s.replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'})[m]);}
socket.emit('join',{room:currentRoom});
socket.on('history',h=>{msgDiv.innerHTML='';h.forEach(m=>addMessage(m.id,m.name,m.text,m.time,m.name===username,m.avatar));});
socket.on('message',m=>addMessage(m.id,m.name,m.text,m.time,m.name===username,m.avatar));
socket.on('system',d=>addSystem(d.text));
socket.on('friend_request',()=>loadRequests());
socket.on('rooms',l=>{let c=document.getElementById('roomsList');c.innerHTML=l.map(r=>`<div class="room-item ${r===currentRoom?'active':''}" data-room="${r}">🏠 ${escape(r)}</div>`).join('');document.querySelectorAll('.room-item').forEach(el=>{el.onclick=()=>{let nr=el.dataset.room;if(nr===currentRoom)return;socket.emit('switch',{old:currentRoom,new:nr});currentRoom=nr;document.getElementById('roomName').innerText=currentRoom;document.querySelectorAll('.room-item').forEach(i=>i.classList.remove('active'));el.classList.add('active');msgDiv.innerHTML='<div class="system-msg">Загрузка...</div>';};});});
socket.on('users',l=>{let c=document.getElementById('usersList');c.innerHTML=l.map(u=>`<div class="user-item" onclick="showUserMenu('${escape(u.name)}', event.clientX, event.clientY)"><span class="online-dot"></span> ${u.avatar||'👤'} ${escape(u.name)} ${u.role==='owner'?'<span class="badge-owner">ВЛ</span>':(u.role==='admin'?'<span class="badge-admin">АДМ</span>':'')}</div>`).join('');});
socket.on('friends',l=>{let c=document.getElementById('friendsList');if(c)c.innerHTML=l.map(f=>`<div class="user-item" onclick="showUserMenu('${escape(f.name)}', event.clientX, event.clientY)">👫 ${escape(f.name)}</div>`).join('');});
socket.on('typing',d=>{if(d.typing)typingUsers[d.name]=true;else delete typingUsers[d.name];let n=Object.keys(typingUsers).filter(n=>n!==username);document.getElementById('typingStatus').innerText=n.length?(n.length===1?`${n[0]} печатает...`:`${n.length} человек печатают...`):'';});
document.getElementById('sendBtn').onclick=()=>{let t=msgInput.value.trim();if(t){socket.emit('message',{text:t,room:currentRoom});msgInput.value='';}};
msgInput.onkeypress=e=>{if(e.key==='Enter')document.getElementById('sendBtn').click();socket.emit('typing',{room:currentRoom,typing:true});clearTimeout(window.tt);window.tt=setTimeout(()=>socket.emit('typing',{room:currentRoom,typing:false}),1000);};
document.getElementById('createRoomBtn')?.addEventListener('click',()=>{let n=document.getElementById('newRoom').value.trim();if(n){socket.emit('create',{room:n});document.getElementById('newRoom').value='';}});
document.getElementById('profileBtn').onclick=()=>document.getElementById('profileModal').style.display='flex';
document.getElementById('settingsBtn').onclick=()=>document.getElementById('settingsModal').style.display='flex';
document.getElementById('closeProfile').onclick=()=>document.getElementById('profileModal').style.display='none';
document.getElementById('closeSettings').onclick=()=>document.getElementById('settingsModal').style.display='none';
document.getElementById('closeUserModal').onclick=()=>document.getElementById('userModal').style.display='none';
document.getElementById('saveProfile').onclick=()=>{fetch('/update_profile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({avatar:document.getElementById('avatarInput').value,bio:document.getElementById('bioInput').value,new_name:document.getElementById('newName').value,new_password:document.getElementById('newPass').value})}).then(r=>r.json()).then(data=>{if(data.success){showToast('Сохранено');location.reload();}else showToast('Ошибка');});};
document.getElementById('clearHistory').onclick=()=>{fetch('/clear_history',{method:'POST'}).then(()=>{showToast('История очищена');location.reload();});};
document.getElementById('logoutBtn').onclick=()=>window.location.href='/logout';
window.onclick=e=>{if(e.target===document.getElementById('profileModal'))document.getElementById('profileModal').style.display='none';if(e.target===document.getElementById('settingsModal'))document.getElementById('settingsModal').style.display='none';if(e.target===document.getElementById('notifyModal'))document.getElementById('notifyModal').style.display='none';if(e.target===document.getElementById('userModal'))document.getElementById('userModal').style.display='none';};
loadRequests();socket.emit('get_rooms');socket.emit('get_users');
</script>
</body>
</html>
'''

@app.route('/')
def index():
    if 'username' not in session: return redirect(url_for('login'))
    u = users.get(session['username'])
    if not u or u.get('banned'): session.clear(); return redirect(url_for('login'))
    return render_template_string(CHAT_HTML, username=session['username'], role=u['role'], avatar=u.get('avatar','👤'), bio=u.get('bio',''))

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
        users[name] = {'password': hashlib.sha256(pwd.encode()).hexdigest(), 'role': 'user', 'avatar': '👤', 'bio': '', 'banned': False, 'muted_until': None, 'online': False}
        save_users(users)
        return redirect(url_for('login'))
    return render_template_string(REGISTER_HTML)

@app.route('/logout')
def logout():
    if 'username' in session:
        users[session['username']]['online'] = False
        save_users(users)
    session.clear(); return redirect(url_for('login'))

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'username' not in session: return jsonify({'error': 'Not logged'})
    name = session['username']; data = request.json
    if data.get('avatar'): users[name]['avatar'] = data['avatar'][:2]
    if data.get('bio') is not None: users[name]['bio'] = data['bio'][:200]
    if data.get('new_name'):
        nn = data['new_name']
        if len(nn)<3 or len(nn)>20: return jsonify({'error': 'Имя 3-20'})
        if nn in users and nn != name: return jsonify({'error': 'Имя занято'})
        users[nn] = users.pop(name); session['username'] = nn
    if data.get('new_password') and len(data['new_password'])>=4: users[session['username']]['password'] = hashlib.sha256(data['new_password'].encode()).hexdigest()
    save_users(users)
    return jsonify({'success': True})

@app.route('/change_id', methods=['POST'])
def change_id():
    if 'username' not in session: return jsonify({'error': 'Not logged'})
    name = session['username']; new_id = request.json.get('new_id')
    if not new_id or not new_id.isdigit() or len(new_id)<4 or len(new_id)>8: return jsonify({'error': 'ID должен быть 4-8 цифр'})
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
    if last_change and datetime.now()-last_change<timedelta(days=14):
        next_change = last_change+timedelta(days=14)
        return jsonify({'can_change': False, 'next_change_date': next_change.strftime("%d.%m.%Y %H:%M")})
    return jsonify({'can_change': True, 'next_change_date': ''})

@app.route('/give_admin', methods=['POST'])
def give_admin():
    if 'username' not in session or users[session['username']]['role']!='owner': return jsonify({'message': 'Только владелец'})
    target = request.json.get('username')
    if target in users and users[target]['role'] not in ['owner','admin']:
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
    if target in users:
        users[target]['muted_until'] = None; save_users(users)
        socketio.emit('system',{'text':f'🔊 {target} размучен!'}, broadcast=True)
        return jsonify({'message': f'{target} размучен'})
    return jsonify({'message': 'Не найден'})

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
    friends.setdefault(name, []); friends.setdefault(target, [])
    if target in friends[name]: return jsonify({'message': 'Уже друг'})
    if name in friends.get(target, []): return jsonify({'message': 'Заявка уже отправлена'})
    friends[target].append(name)
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

@app.route('/remove_friend', methods=['POST'])
def remove_friend():
    if 'username' not in session: return jsonify({'message': 'Войдите'})
    name = session['username']; target = request.json.get('friend')
    if target in friends.get(name, []):
        friends[name].remove(target)
        friends[target].remove(name)
        save_friends(friends)
        return jsonify({'message': f'{target} удалён из друзей'})
    return jsonify({'message': 'Не в друзьях'})

@app.route('/get_friend_requests')
def get_friend_requests():
    if 'username' not in session: return jsonify({'requests': []})
    name = session['username']
    return jsonify({'requests': friends.get(name, [])})

@app.route('/user_info/<name>')
def user_info(name):
    if name not in users: return jsonify({'error': 'Not found'})
    u = users[name]
    is_friend = name in friends.get(session.get('username',''), []) if session.get('username') else False
    role_display = {'owner':'Владелец','admin':'Админ','user':'Пользователь'}.get(u['role'],'Пользователь')
    return jsonify({'username':name, 'bio':u.get('bio',''), 'role_display':role_display, 'role':u['role'], 'avatar':u.get('avatar','👤'), 'friends_count':len(friends.get(name,[])), 'is_friend':is_friend, 'banned':u.get('banned',False), 'muted':u.get('muted_until') and datetime.now()<datetime.fromisoformat(u['muted_until'])})

@app.route('/clear_history', methods=['POST'])
def clear_history():
    if 'username' not in session: return jsonify({'success': False})
    global messages
    messages = {'Главная': []}
    save_messages(messages)
    return jsonify({'success': True})

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
        emit('system', {'text': '🔇 Вы замучены!'}, to=request.sid); return
    room = data['room']; text = data['text']
    msg_id = str(int(datetime.now().timestamp()*1000))
    msg = {'id': msg_id, 'name': username, 'text': text, 'time': datetime.now().strftime('%H:%M'), 'avatar': users[username].get('avatar','👤')}
    if room not in messages: messages[room] = []
    messages[room].append(msg)
    if len(messages[room])>100: messages[room] = messages[room][-100:]
    save_messages(messages)
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
    for name,u in users.items():
        if not u.get('banned') and u.get('online', False):
            lst.append({'name': name, 'role': u['role'], 'avatar': u.get('avatar','👤')})
    emit('users', lst, broadcast=True)
    if session.get('username'):
        name = session['username']
        friends_list = [{'name': f} for f in friends.get(name, [])]
        emit('friends', friends_list, to=request.sid)

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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
