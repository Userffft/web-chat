from flask import Flask, render_template_string, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import os
import json
import hashlib
import base64

app = Flask(__name__)
app.secret_key = 'chatic-super-secret-key-2024'
socketio = SocketIO(app, cors_allowed_origins="*")

# Файлы для хранения данных
USERS_FILE = 'users.json'
MESSAGES_FILE = 'messages.json'
ROOMS_FILE = 'rooms.json'
DMS_FILE = 'dms.json'  # Личные сообщения
SETTINGS_FILE = 'settings.json'  # Настройки пользователей

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {
        'dimooon': {
            'password': hashlib.sha256('1111'.encode()).hexdigest(),
            'role': 'owner',
            'avatar': '👑',
            'banned': False,
            'theme': 'light',
            'notifications': True,
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
    return {'Общая': [], 'Случайная': [], 'Помощь': []}

def save_messages(messages):
    with open(MESSAGES_FILE, 'w') as f:
        json.dump(messages, f)

def load_rooms():
    if os.path.exists(ROOMS_FILE):
        with open(ROOMS_FILE, 'r') as f:
            return json.load(f)
    return ['Общая', 'Случайная', 'Помощь']

def save_rooms(rooms):
    with open(ROOMS_FILE, 'w') as f:
        json.dump(rooms, f)

def load_dms():
    if os.path.exists(DMS_FILE):
        with open(DMS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_dms(dms):
    with open(DMS_FILE, 'w') as f:
        json.dump(dms, f)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f)

users = load_users()
messages = load_messages()
rooms = load_rooms()
dms = load_dms()
settings = load_settings()

# HTML шаблоны (сокращённо из-за длины, но полная версия ниже)
LOGIN_TEMPLATE = '''...'''  # Полный код будет в финальном сообщении
REGISTER_TEMPLATE = '''...'''
CHAT_TEMPLATE = '''...'''

# Маршруты Flask (все)
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    user = users.get(session['username'])
    if not user or user.get('banned'):
        session.clear()
        return redirect(url_for('login'))
    role_display = {'owner': 'Владелец', 'admin': 'Администратор', 'moderator': 'Модератор', 'user': 'Пользователь'}.get(user['role'], 'Пользователь')
    user_settings = settings.get(session['username'], {'theme': 'light', 'notifications': True})
    return render_template_string(CHAT_TEMPLATE, 
                                 username=session['username'],
                                 role=user['role'],
                                 role_display=role_display,
                                 avatar=user.get('avatar', '💬'),
                                 theme=user_settings.get('theme', 'light'),
                                 notifications=user_settings.get('notifications', True))

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
            return render_template_string(REGISTER_TEMPLATE, error='Имя должно быть от 3 до 20 символов')
        if len(password) < 4:
            return render_template_string(REGISTER_TEMPLATE, error='Пароль должен быть минимум 4 символа')
        users[username] = {
            'password': hashlib.sha256(password.encode()).hexdigest(),
            'role': 'user',
            'avatar': '👤',
            'banned': False,
            'theme': 'light',
            'notifications': True,
            'created_at': datetime.now().isoformat()
        }
        save_users(users)
        return redirect(url_for('login'))
    return render_template_string(REGISTER_TEMPLATE, error=None)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/make_admin/<username>')
def make_admin(username):
    if username in users:
        users[username]['role'] = 'admin'
        save_users(users)
        return f'✅ {username} теперь администратор!'
    return f'❌ {username} не найден'

@app.route('/save_settings', methods=['POST'])
def save_settings_route():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.json
    username = session['username']
    if username not in settings:
        settings[username] = {}
    if 'theme' in data:
        settings[username]['theme'] = data['theme']
        users[username]['theme'] = data['theme']
    if 'notifications' in data:
        settings[username]['notifications'] = data['notifications']
        users[username]['notifications'] = data['notifications']
    save_settings(settings)
    save_users(users)
    return jsonify({'success': True})

# SocketIO события
@socketio.on('join')
def handle_join(data):
    username = session.get('username')
    if not username or users.get(username, {}).get('banned'):
        return
    room = data['room']
    join_room(room)
    emit('history', messages.get(room, []), to=request.sid)

@socketio.on('message')
def handle_message(data):
    username = session.get('username')
    if not username or users.get(username, {}).get('banned'):
        return
    room = data['room']
    text = data['text']
    reply_to = data.get('reply_to')
    if len(text) > 500:
        emit('system', 'Сообщение слишком длинное', to=request.sid)
        return
    msg_id = str(int(datetime.now().timestamp() * 1000))
    message = {
        'id': msg_id,
        'name': username,
        'text': text,
        'time': datetime.now().strftime('%H:%M:%S'),
        'role': users[username]['role'],
        'avatar': users[username].get('avatar', '👤'),
        'reply_to': reply_to
    }
    
    # Обработка упоминаний
    mentions = []
    words = text.split()
    for word in words:
        if word.startswith('@'):
            mention_name = word[1:]
            if mention_name in users:
                mentions.append(mention_name)
                emit('notification', {'from': username, 'message': f'Упомянул вас: {text[:50]}'}, to=mention_name)
    
    message['mentions'] = mentions
    
    messages.setdefault(room, []).append(message)
    if len(messages[room]) > 200:
        messages[room] = messages[room][-200:]
    save_messages(messages)
    emit('message', message, to=room, broadcast=True)

@socketio.on('delete_message')
def handle_delete(data):
    username = session.get('username')
    if not username:
        return
    role = users[username]['role']
    msg_id = data['messageId']
    room = data['room']
    for i, msg in enumerate(messages.get(room, [])):
        if msg.get('id') == msg_id:
            if role == 'owner' or (role == 'admin' and msg['name'] != username) or msg['name'] == username:
                messages[room].pop(i)
                save_messages(messages)
                emit('system', f'Сообщение от {msg["name"]} удалено', to=room, broadcast=True)
            break

@socketio.on('edit_message')
def handle_edit(data):
    username = session.get('username')
    if not username:
        return
    msg_id = data['messageId']
    room = data['room']
    new_text = data['new_text']
    for msg in messages.get(room, []):
        if msg.get('id') == msg_id and msg['name'] == username:
            msg['text'] = new_text + ' (отредактировано)'
            save_messages(messages)
            emit('message_update', {'id': msg_id, 'text': msg['text']}, to=room, broadcast=True)
            break

@socketio.on('pin_message')
def handle_pin(data):
    username = session.get('username')
    if not username or users[username]['role'] not in ['owner', 'admin']:
        return
    msg_id = data['messageId']
    room = data['room']
    for msg in messages.get(room, []):
        if msg.get('id') == msg_id:
            msg['pinned'] = True
            save_messages(messages)
            emit('system', f'Сообщение от {msg["name"]} закреплено', to=room, broadcast=True)
            break

@socketio.on('ban_user')
def handle_ban(data):
    username = session.get('username')
    if not username or users[username]['role'] not in ['owner', 'admin']:
        return
    target = data['username']
    room = data.get('room', 'Общая')
    if target in users and users[target]['role'] != 'owner':
        users[target]['banned'] = True
        save_users(users)
        emit('system', f'{target} заблокирован', to=room, broadcast=True)

@socketio.on('typing')
def handle_typing(data):
    username = session.get('username')
    if not username:
        return
    emit('typing', {'name': username, 'typing': data['typing']}, to=data['room'], broadcast=True, include_self=False)

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
        emit('rooms_list', rooms, broadcast=True)

@socketio.on('get_rooms')
def handle_get_rooms():
    emit('rooms_list', rooms)

@socketio.on('get_users')
def handle_get_users():
    users_list = [{'name': name, 'role': data['role'], 'avatar': data.get('avatar', '👤')} 
                  for name, data in users.items() if not data.get('banned')]
    emit('users_list', users_list)

# Личные сообщения
@socketio.on('private_message')
def handle_private_message(data):
    username = session.get('username')
    if not username:
        return
    target = data['target']
    text = data['text']
    if target not in users:
        return
    msg_id = str(int(datetime.now().timestamp() * 1000))
    message = {
        'id': msg_id,
        'from': username,
        'to': target,
        'text': text,
        'time': datetime.now().strftime('%H:%M:%S'),
        'read': False
    }
    dm_key = f"{min(username, target)}_{max(username, target)}"
    if dm_key not in dms:
        dms[dm_key] = []
    dms[dm_key].append(message)
    save_dms(dms)
    
    emit('private_message', message, to=target)
    emit('private_message_sent', message, to=username)

@socketio.on('get_private_messages')
def handle_get_private_messages(data):
    username = session.get('username')
    if not username:
        return
    target = data['target']
    dm_key = f"{min(username, target)}_{max(username, target)}"
    emit('private_messages_list', dms.get(dm_key, []))

@socketio.on('image_message')
def handle_image_message(data):
    username = session.get('username')
    if not username:
        return
    room = data['room']
    image_data = data['image']  # base64
    msg_id = str(int(datetime.now().timestamp() * 1000))
    message = {
        'id': msg_id,
        'name': username,
        'text': '📷 Изображение',
        'image': image_data,
        'time': datetime.now().strftime('%H:%M:%S'),
        'role': users[username]['role'],
        'avatar': users[username].get('avatar', '👤')
    }
    messages.setdefault(room, []).append(message)
    save_messages(messages)
    emit('message', message, to=room, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
