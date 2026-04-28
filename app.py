from flask import Flask, render_template, request, session, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import sqlite3
import json
import os
from functools import wraps
import random
import string
from typing import Dict, List, Tuple

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-in-production')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Инициализация SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Инициализация LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите в систему'

# База данных
DATABASE = 'chat.db'

def get_db():
    """Получение соединения с базой данных"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Инициализация базы данных"""
    with get_db() as conn:
        # Таблица пользователей
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT,
                avatar TEXT,
                status TEXT DEFAULT 'online',
                is_admin INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица сообщений
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                message TEXT,
                room TEXT DEFAULT 'general',
                is_private INTEGER DEFAULT 0,
                file_url TEXT,
                file_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Таблица комнат
        conn.execute('''
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_by INTEGER,
                is_private INTEGER DEFAULT 0,
                password TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')
        
        # Таблица приватных сообщений
        conn.execute('''
            CREATE TABLE IF NOT EXISTS private_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user_id INTEGER,
                to_user_id INTEGER,
                message TEXT,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (from_user_id) REFERENCES users (id),
                FOREIGN KEY (to_user_id) REFERENCES users (id)
            )
        ''')
        
        # Таблица блокировок
        conn.execute('''
            CREATE TABLE IF NOT EXISTS blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                blocker_id INTEGER,
                blocked_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (blocker_id) REFERENCES users (id),
                FOREIGN KEY (blocked_id) REFERENCES users (id),
                UNIQUE(blocker_id, blocked_id)
            )
        ''')
        
        # Добавление тестового пользователя, если его нет
        admin = conn.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()
        if not admin:
            conn.execute(
                'INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)',
                ('admin', generate_password_hash('admin123'), 1)
            )
        
        # Добавление общей комнаты по умолчанию
        general_room = conn.execute('SELECT * FROM rooms WHERE name = ?', ('general',)).fetchone()
        if not general_room:
            conn.execute(
                'INSERT INTO rooms (name, description, is_private) VALUES (?, ?, ?)',
                ('general', 'Общий чат для всех пользователей', 0)
            )
        
        conn.commit()

# Модель пользователя для Flask-Login
class User(UserMixin):
    def __init__(self, id, username, is_admin=False):
        self.id = id
        self.username = username
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(user_id):
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if user:
            return User(user['id'], user['username'], user['is_admin'])
    return None

# Декоратор для проверки прав администратора
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'error': 'Доступ запрещен'}), 403
        return f(*args, **kwargs)
    return decorated_function

# Маршруты
@app.route('/')
def index():
    """Главная страница"""
    if current_user.is_authenticated:
        return render_template('chat.html')
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
            
            if user and check_password_hash(user['password'], password):
                login_user(User(user['id'], user['username'], user['is_admin']))
                
                # Обновляем статус
                conn.execute('UPDATE users SET status = ?, last_seen = CURRENT_TIMESTAMP WHERE id = ?', 
                           ('online', user['id']))
                conn.commit()
                
                # Уведомляем всех о входе пользователя
                socketio.emit('user_status_change', {
                    'user_id': user['id'],
                    'username': user['username'],
                    'status': 'online'
                })
                
                return jsonify({'success': True, 'redirect': '/'})
            else:
                return jsonify({'success': False, 'error': 'Неверное имя пользователя или пароль'})
    
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    """Регистрация нового пользователя"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    
    if not username or not password:
        return jsonify({'error': 'Имя пользователя и пароль обязательны'}), 400
    
    with get_db() as conn:
        # Проверяем существование пользователя
        existing = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if existing:
            return jsonify({'error': 'Пользователь с таким именем уже существует'}), 400
        
        # Создаем нового пользователя
        conn.execute(
            'INSERT INTO users (username, password, email) VALUES (?, ?, ?)',
            (username, generate_password_hash(password), email)
        )
        conn.commit()
        
        return jsonify({'success': True})

@app.route('/logout')
@login_required
def logout():
    """Выход из системы"""
    user_id = current_user.id
    username = current_user.username
    
    # Обновляем статус
    with get_db() as conn:
        conn.execute('UPDATE users SET status = ?, last_seen = CURRENT_TIMESTAMP WHERE id = ?', 
                   ('offline', user_id))
        conn.commit()
    
    # Уведомляем всех о выходе пользователя
    socketio.emit('user_status_change', {
        'user_id': user_id,
        'username': username,
        'status': 'offline'
    })
    
    logout_user()
    return jsonify({'success': True})

@app.route('/api/messages')
@login_required
def get_messages():
    """Получение последних сообщений"""
    room = request.args.get('room', 'general')
    limit = request.args.get('limit', 50, type=int)
    
    with get_db() as conn:
        messages = conn.execute('''
            SELECT m.*, u.avatar 
            FROM messages m
            LEFT JOIN users u ON m.user_id = u.id
            WHERE m.room = ? AND m.is_private = 0
            ORDER BY m.created_at DESC
            LIMIT ?
        ''', (room, limit)).fetchall()
        
        return jsonify([dict(msg) for msg in messages[::-1]])

@app.route('/api/users')
@login_required
def get_users():
    """Получение списка пользователей"""
    with get_db() as conn:
        users = conn.execute('''
            SELECT id, username, status, is_admin, last_seen 
            FROM users 
            WHERE id != ?
            ORDER BY status = 'online' DESC, username
        ''', (current_user.id,)).fetchall()
        
        # Проверяем блокировки
        blocked_users = conn.execute('''
            SELECT blocked_id FROM blocks WHERE blocker_id = ?
        ''', (current_user.id,)).fetchall()
        
        blocked_ids = [b['blocked_id'] for b in blocked_users]
        
        users_list = []
        for user in users:
            user_dict = dict(user)
            user_dict['is_blocked'] = user['id'] in blocked_ids
            users_list.append(user_dict)
        
        return jsonify(users_list)

@app.route('/api/rooms')
@login_required
def get_rooms():
    """Получение списка комнат"""
    with get_db() as conn:
        rooms = conn.execute('''
            SELECT r.*, u.username as creator_name
            FROM rooms r
            LEFT JOIN users u ON r.created_by = u.id
            WHERE r.is_private = 0 OR r.created_by = ?
            ORDER BY r.name
        ''', (current_user.id,)).fetchall()
        
        return jsonify([dict(room) for room in rooms])

@app.route('/api/create_room', methods=['POST'])
@login_required
def create_room():
    """Создание новой комнаты"""
    data = request.json
    name = data.get('name')
    description = data.get('description', '')
    is_private = data.get('is_private', False)
    password = data.get('password') if is_private else None
    
    if not name:
        return jsonify({'error': 'Имя комнаты обязательно'}), 400
    
    with get_db() as conn:
        existing = conn.execute('SELECT * FROM rooms WHERE name = ?', (name,)).fetchone()
        if existing:
            return jsonify({'error': 'Комната с таким именем уже существует'}), 400
        
        conn.execute('''
            INSERT INTO rooms (name, description, created_by, is_private, password)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, description, current_user.id, is_private, password))
        conn.commit()
        
        # Уведомляем всех о создании комнаты
        socketio.emit('room_created', {
            'name': name,
            'description': description,
            'creator': current_user.username
        })
        
        return jsonify({'success': True})

@app.route('/api/block_user', methods=['POST'])
@login_required
def block_user():
    """Блокировка пользователя"""
    data = request.json
    user_id = data.get('user_id')
    
    if user_id == current_user.id:
        return jsonify({'error': 'Нельзя заблокировать самого себя'}), 400
    
    with get_db() as conn:
        conn.execute('INSERT OR IGNORE INTO blocks (blocker_id, blocked_id) VALUES (?, ?)',
                    (current_user.id, user_id))
        conn.commit()
        
        return jsonify({'success': True})

@app.route('/api/unblock_user', methods=['POST'])
@login_required
def unblock_user():
    """Разблокировка пользователя"""
    data = request.json
    user_id = data.get('user_id')
    
    with get_db() as conn:
        conn.execute('DELETE FROM blocks WHERE blocker_id = ? AND blocked_id = ?',
                    (current_user.id, user_id))
        conn.commit()
        
        return jsonify({'success': True})

@app.route('/api/private_chats')
@login_required
def get_private_chats():
    """Получение списка приватных чатов"""
    with get_db() as conn:
        # Получаем последние приватные сообщения
        chats = conn.execute('''
            SELECT 
                CASE 
                    WHEN pm.from_user_id = ? THEN pm.to_user_id
                    ELSE pm.from_user_id
                END as other_user_id,
                MAX(pm.created_at) as last_message_time,
                COUNT(CASE WHEN pm.is_read = 0 AND pm.to_user_id = ? THEN 1 END) as unread_count,
                u.username as other_username,
                u.status as other_status
            FROM private_messages pm
            JOIN users u ON (CASE WHEN pm.from_user_id = ? THEN pm.to_user_id ELSE pm.from_user_id END) = u.id
            WHERE pm.from_user_id = ? OR pm.to_user_id = ?
            GROUP BY other_user_id
            ORDER BY last_message_time DESC
        ''', (current_user.id, current_user.id, current_user.id, current_user.id, current_user.id)).fetchall()
        
        return jsonify([dict(chat) for chat in chats])

# SocketIO события
@socketio.on('connect')
def handle_connect():
    """Обработка подключения"""
    if current_user.is_authenticated:
        with get_db() as conn:
            conn.execute('UPDATE users SET status = ?, last_seen = CURRENT_TIMESTAMP WHERE id = ?',
                       ('online', current_user.id))
            conn.commit()
        
        join_room('general')
        emit('user_connected', {
            'user_id': current_user.id,
            'username': current_user.username
        }, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    """Обработка отключения"""
    if current_user.is_authenticated:
        with get_db() as conn:
            conn.execute('UPDATE users SET status = ?, last_seen = CURRENT_TIMESTAMP WHERE id = ?',
                       ('offline', current_user.id))
            conn.commit()
        
        emit('user_disconnected', {
            'user_id': current_user.id,
            'username': current_user.username
        }, broadcast=True)

@socketio.on('send_message')
def handle_send_message(data):
    """Отправка сообщения"""
    if not current_user.is_authenticated:
        return
    
    message = data.get('message', '').strip()
    room = data.get('room', 'general')
    is_private = data.get('is_private', False)
    to_user_id = data.get('to_user_id')
    
    if not message:
        return
    
    # Сохраняем сообщение в БД
    with get_db() as conn:
        # Проверяем блокировки
        if to_user_id:
            blocked = conn.execute('''
                SELECT * FROM blocks 
                WHERE (blocker_id = ? AND blocked_id = ?) OR (blocker_id = ? AND blocked_id = ?)
            ''', (current_user.id, to_user_id, to_user_id, current_user.id)).fetchone()
            
            if blocked:
                emit('error', {'message': 'Вы не можете отправить сообщение этому пользователю'})
                return
        
        if is_private and to_user_id:
            conn.execute('''
                INSERT INTO private_messages (from_user_id, to_user_id, message)
                VALUES (?, ?, ?)
            ''', (current_user.id, to_user_id, message))
            
            # Отправляем уведомление получателю
            emit('private_message', {
                'from_user_id': current_user.id,
                'from_username': current_user.username,
                'message': message,
                'timestamp': datetime.now().isoformat()
            }, room=f'user_{to_user_id}')
        else:
            conn.execute('''
                INSERT INTO messages (user_id, username, message, room)
                VALUES (?, ?, ?, ?)
            ''', (current_user.id, current_user.username, message, room))
            
            # Отправляем сообщение всем в комнате
            emit('new_message', {
                'user_id': current_user.id,
                'username': current_user.username,
                'message': message,
                'room': room,
                'timestamp': datetime.now().isoformat()
            }, room=room)
        
        conn.commit()

@socketio.on('join_room')
def handle_join_room(data):
    """Присоединение к комнате"""
    room = data.get('room')
    password = data.get('password')
    
    if not room:
        return
    
    with get_db() as conn:
        room_data = conn.execute('SELECT * FROM rooms WHERE name = ?', (room,)).fetchone()
        
        if room_data and room_data['is_private']:
            if room_data['password'] != password:
                emit('error', {'message': 'Неверный пароль комнаты'})
                return
        
        join_room(room)
        emit('joined_room', {'room': room})
        
        # Загружаем историю сообщений комнаты
        messages = conn.execute('''
            SELECT m.*, u.avatar 
            FROM messages m
            LEFT JOIN users u ON m.user_id = u.id
            WHERE m.room = ? AND m.is_private = 0
            ORDER BY m.created_at DESC
            LIMIT 50
        ''', (room,)).fetchall()
        
        emit('room_history', [dict(msg) for msg in messages[::-1]])

@socketio.on('leave_room')
def handle_leave_room(data):
    """Покидание комнаты"""
    room = data.get('room')
    if room:
        leave_room(room)
        emit('left_room', {'room': room})

@socketio.on('typing')
def handle_typing(data):
    """Уведомление о наборе текста"""
    room = data.get('room')
    is_typing = data.get('is_typing', False)
    
    emit('user_typing', {
        'user_id': current_user.id,
        'username': current_user.username,
        'is_typing': is_typing
    }, room=room, include_self=False)

@socketio.on('mark_read')
def handle_mark_read(data):
    """Отметка сообщений как прочитанных"""
    message_id = data.get('message_id')
    
    if message_id:
        with get_db() as conn:
            conn.execute('UPDATE private_messages SET is_read = 1 WHERE id = ? AND to_user_id = ?',
                        (message_id, current_user.id))
            conn.commit()

# Инициализация БД при запуске
init_db()

# Создание шаблонов
os.makedirs('templates', exist_ok=True)

# Шаблон login.html
with open('templates/login.html', 'w', encoding='utf-8') as f:
    f.write('''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Вход в чат</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
            width: 400px;
            max-width: 90%;
        }
        
        .tabs {
            display: flex;
            border-bottom: 2px solid #f0f0f0;
        }
        
        .tab {
            flex: 1;
            padding: 15px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: 600;
            color: #666;
        }
        
        .tab.active {
            color: #667eea;
            border-bottom: 2px solid #667eea;
        }
        
        .form-container {
            padding: 30px;
        }
        
        .form {
            display: none;
        }
        
        .form.active {
            display: block;
        }
        
        input {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        button:hover {
            transform: translateY(-2px);
        }
        
        .error {
            color: #e74c3c;
            font-size: 14px;
            margin-top: 10px;
            text-align: center;
        }
        
        h2 {
            text-align: center;
            margin-bottom: 20px;
            color: #333;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="tabs">
            <div class="tab active" onclick="switchTab('login')">Вход</div>
            <div class="tab" onclick="switchTab('register')">Регистрация</div>
        </div>
        
        <div class="form-container">
            <form id="login-form" class="form active">
                <h2>Добро пожаловать!</h2>
                <input type="text" id="login-username" placeholder="Имя пользователя" required>
                <input type="password" id="login-password" placeholder="Пароль" required>
                <button type="submit">Войти</button>
                <div id="login-error" class="error"></div>
            </form>
            
            <form id="register-form" class="form">
                <h2>Создать аккаунт</h2>
                <input type="text" id="reg-username" placeholder="Имя пользователя" required>
                <input type="email" id="reg-email" placeholder="Email (опционально)">
                <input type="password" id="reg-password" placeholder="Пароль" required>
                <input type="password" id="reg-confirm" placeholder="Подтвердите пароль" required>
                <button type="submit">Зарегистрироваться</button>
                <div id="register-error" class="error"></div>
            </form>
        </div>
    </div>
    
    <script>
        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.form').forEach(f => f.classList.remove('active'));
            
            if (tab === 'login') {
                document.querySelector('.tab:first-child').classList.add('active');
                document.getElementById('login-form').classList.add('active');
            } else {
                document.querySelector('.tab:last-child').classList.add('active');
                document.getElementById('register-form').classList.add('active');
            }
        }
        
        document.getElementById('login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('login-username').value;
            const password = document.getElementById('login-password').value;
            
            const formData = new FormData();
            formData.append('username', username);
            formData.append('password', password);
            
            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                
                if (data.success) {
                    window.location.href = data.redirect;
                } else {
                    document.getElementById('login-error').textContent = data.error;
                }
            } catch (error) {
                document.getElementById('login-error').textContent = 'Ошибка соединения';
            }
        });
        
        document.getElementById('register-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('reg-username').value;
            const email = document.getElementById('reg-email').value;
            const password = document.getElementById('reg-password').value;
            const confirm = document.getElementById('reg-confirm').value;
            
            if (password !== confirm) {
                document.getElementById('register-error').textContent = 'Пароли не совпадают';
                return;
            }
            
            try {
                const response = await fetch('/register', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username, email, password})
                });
                const data = await response.json();
                
                if (data.success) {
                    alert('Регистрация успешна! Теперь войдите в систему.');
                    switchTab('login');
                } else {
                    document.getElementById('register-error').textContent = data.error;
                }
            } catch (error) {
                document.getElementById('register-error').textContent = 'Ошибка соединения';
            }
        });
    </script>
</body>
</html>
    ''')

# Шаблон chat.html
with open('templates/chat.html', 'w', encoding='utf-8') as f:
    f.write('''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Веб-Чат</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f0f2f5;
            height: 100vh;
            overflow: hidden;
        }
        
        .app {
            display: flex;
            height: 100vh;
        }
        
        /* Боковая панель */
        .sidebar {
            width: 280px;
            background: white;
            border-right: 1px solid #e0e0e0;
            display: flex;
            flex-direction: column;
            box-shadow: 2px 0 5px rgba(0,0,0,0.05);
        }
        
        .user-info {
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .username {
            font-weight: bold;
            font-size: 18px;
        }
        
        .logout-btn {
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            padding: 8px 12px;
            border-radius: 8px;
            cursor: pointer;
            transition: background 0.3s;
        }
        
        .logout-btn:hover {
            background: rgba(255,255,255,0.3);
        }
        
        .sidebar-nav {
            padding: 20px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .nav-btn {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px;
            margin: 5px 0;
            border: none;
            background: none;
            width: 100%;
            text-align: left;
            cursor: pointer;
            border-radius: 8px;
            transition: background 0.3s;
            font-size: 14px;
        }
        
        .nav-btn:hover {
            background: #f0f2f5;
        }
        
        .nav-btn.active {
            background: #e8eaf6;
            color: #667eea;
        }
        
        .rooms-list, .users-list {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
        }
        
        .room-item, .user-item {
            padding: 12px;
            margin: 5px 0;
            cursor: pointer;
            border-radius: 8px;
            transition: background 0.3s;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .room-item:hover, .user-item:hover {
            background: #f0f2f5;
        }
        
        .room-item.active {
            background: #e8eaf6;
            color: #667eea;
        }
        
        .user-status {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-online { background: #4caf50; }
        .status-offline { background: #9e9e9e; }
        
        .section-title {
            padding: 10px;
            font-weight: bold;
            color: #666;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        /* Основная область чата */
        .chat-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: #f0f2f5;
        }
        
        .chat-header {
            background: white;
            padding: 20px;
            border-bottom: 1px solid #e0e0e0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        
        .chat-header h2 {
            font-size: 18px;
            color: #333;
        }
        
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
        }
        
        .message {
            margin-bottom: 15px;
            display: flex;
            animation: fadeIn 0.3s;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .message-content {
            max-width: 60%;
            padding: 10px 15px;
            border-radius: 18px;
            word-wrap: break-word;
        }
        
        .message-own {
            justify-content: flex-end;
        }
        
        .message-own .message-content {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .message-other .message-content {
            background: white;
            color: #333;
        }
        
        .message-info {
            font-size: 12px;
            margin-bottom: 5px;
            padding-left: 5px;
        }
        
        .message-username {
            font-weight: bold;
            color: #667eea;
        }
        
        .message-time {
            color: #999;
            font-size: 10px;
            margin-left: 10px;
        }
        
        /* Область ввода */
        .input-area {
            padding: 20px;
            background: white;
            border-top: 1px solid #e0e0e0;
            display: flex;
            gap: 10px;
        }
        
        .input-area input {
            flex: 1;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            font-size: 14px;
            outline: none;
            transition: border-color 0.3s;
        }
        
        .input-area input:focus {
            border-color: #667eea;
        }
        
        .input-area button {
            padding: 12px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-weight: bold;
            transition: transform 0.2s;
        }
        
        .input-area button:hover {
            transform: translateY(-2px);
        }
        
        .typing-indicator {
            padding: 10px 20px;
            color: #999;
            font-size: 12px;
            font-style: italic;
        }
        
        /* Модальные окна */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        
        .modal-content {
            background: white;
            padding: 30px;
            border-radius: 20px;
            width: 400px;
            max-width: 90%;
        }
        
        .modal-content input, .modal-content textarea {
            width: 100%;
            padding: 10px;
            margin: 10px 0;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
        }
        
        .modal-buttons {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        
        .modal-buttons button {
            flex: 1;
            padding: 10px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
        }
        
        .context-menu {
            position: fixed;
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            box-shadow: 0 5px 10px rgba(0,0,0,0.1);
            display: none;
            z-index: 1000;
        }
        
        .context-menu-item {
            padding: 10px 20px;
            cursor: pointer;
            transition: background 0.2s;
        }
        
        .context-menu-item:hover {
            background: #f0f2f5;
        }
        
        .scrollable {
            overflow-y: auto;
        }
        
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #f1f1f1;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #555;
        }
    </style>
</head>
<body>
    <div class="app">
        <div class="sidebar">
            <div class="user-info">
                <span class="username" id="current-username">Загрузка...</span>
                <button class="logout-btn" onclick="logout()">Выйти</button>
            </div>
            
            <div class="sidebar-nav">
                <button class="nav-btn active" onclick="switchSection('rooms')">💬 Комнаты</button>
                <button class="nav-btn" onclick="switchSection('users')">👥 Пользователи</button>
            </div>
            
            <div id="rooms-section" class="rooms-list scrollable">
                <div class="section-title">Доступные комнаты</div>
                <div id="rooms-list"></div>
                <button class="nav-btn" onclick="showCreateRoomModal()" style="margin-top: 10px;">➕ Создать комнату</button>
            </div>
            
            <div id="users-section" class="users-list scrollable" style="display: none;">
                <div class="section-title">Пользователи онлайн</div>
                <div id="users-list"></div>
            </div>
        </div>
        
        <div class="chat-area">
            <div class="chat-header">
                <h2 id="current-room">Общий чат</h2>
            </div>
            
            <div id="messages" class="messages scrollable"></div>
            
            <div id="typing-indicator" class="typing-indicator"></div>
            
            <div class="input-area">
                <input type="text" id="message-input" placeholder="Введите сообщение..." onkeypress="handleKeyPress(event)">
                <button onclick="sendMessage()">Отправить</button>
            </div>
        </div>
    </div>
    
    <!-- Модальное окно создания комнаты -->
    <div id="create-room-modal" class="modal">
        <div class="modal-content">
            <h3>Создать комнату</h3>
            <input type="text" id="room-name" placeholder="Название комнаты">
            <textarea id="room-description" placeholder="Описание комнаты" rows="3"></textarea>
            <label>
                <input type="checkbox" id="room-private"> Приватная комната
            </label>
            <input type="password" id="room-password" placeholder="Пароль (для приватной комнаты)" style="display: none;">
            <div class="modal-buttons">
                <button onclick="createRoom()">Создать</button>
                <button onclick="closeModal('create-room-modal')">Отмена</button>
            </div>
        </div>
    </div>
    
    <div id="context-menu" class="context-menu">
        <div class="context-menu-item" onclick="blockUser()">Заблокировать пользователя</div>
    </div>
    
    <script>
        let socket;
        let currentRoom = 'general';
        let currentUser = null;
        let typingTimeout = null;
        let selectedUserId = null;
        
        // Инициализация
        async function init() {
            await loadUserInfo();
            connectSocket();
            await loadRooms();
            await loadUsers();
            loadMessages();
            
            // Обновление каждые 5 секунд
            setInterval(loadUsers, 5000);
        }
        
        async function loadUserInfo() {
            const response = await fetch('/api/current-user');
            // Получаем из куки или session
            document.getElementById('current-username').textContent = 'User';
        }
        
        function connectSocket() {
            socket = io();
            
            socket.on('connect', () => {
                console.log('Connected to server');
                socket.emit('join_room', {room: currentRoom});
            });
            
            socket.on('new_message', (data) => {
                if (data.room === currentRoom) {
                    addMessage(data);
                }
            });
            
            socket.on('private_message', (data) => {
                addPrivateMessageNotification(data);
            });
            
            socket.on('user_connected', (data) => {
                loadUsers();
                addSystemMessage(`${data.username} присоединился к чату`);
            });
            
            socket.on('user_disconnected', (data) => {
                loadUsers();
                addSystemMessage(`${data.username} покинул чат`);
            });
            
            socket.on('user_typing', (data) => {
                showTypingIndicator(data);
            });
            
            socket.on('room_history', (messages) => {
                messages.forEach(msg => addMessage(msg, false));
            });
            
            socket.on('room_created', (data) => {
                loadRooms();
                addSystemMessage(`Создана новая комната: ${data.name}`);
            });
        }
        
        async function loadRooms() {
            const response = await fetch('/api/rooms');
            const rooms = await response.json();
            
            const roomsList = document.getElementById('rooms-list');
            roomsList.innerHTML = '';
            
            rooms.forEach(room => {
                const roomDiv = document.createElement('div');
                roomDiv.className = 'room-item' + (room.name === currentRoom ? ' active' : '');
                roomDiv.innerHTML = `
                    <span>${room.name === 'general' ? '🌍 ' : '🔒 '}${room.name}</span>
                    ${room.is_private ? '🔐' : ''}
                `;
                roomDiv.onclick = () => switchRoom(room.name);
                roomsList.appendChild(roomDiv);
            });
        }
        
        async function loadUsers() {
            const response = await fetch('/api/users');
            const users = await response.json();
            
            const usersList = document.getElementById('users-list');
            usersList.innerHTML = '';
            
            const onlineUsers = users.filter(u => u.status === 'online');
            const offlineUsers = users.filter(u => u.status === 'offline');
            
            if (onlineUsers.length > 0) {
                const onlineDiv = document.createElement('div');
                onlineDiv.className = 'section-title';
                onlineDiv.textContent = 'В сети';
                usersList.appendChild(onlineDiv);
                
                onlineUsers.forEach(user => {
                    usersList.appendChild(createUserElement(user));
                });
            }
            
            if (offlineUsers.length > 0) {
                const offlineDiv = document.createElement('div');
                offlineDiv.className = 'section-title';
                offlineDiv.textContent = 'Не в сети';
                usersList.appendChild(offlineDiv);
                
                offlineUsers.forEach(user => {
                    usersList.appendChild(createUserElement(user));
                });
            }
        }
        
        function createUserElement(user) {
            const userDiv = document.createElement('div');
            userDiv.className = 'user-item';
            userDiv.innerHTML = `
                <div>
                    <span class="user-status status-${user.status}"></span>
                    <span>${user.username}${user.is_admin ? ' 👑' : ''}</span>
                </div>
                <div>
                    <button onclick="startPrivateChat(${user.id}, '${user.username}')">💬</button>
                    <button onclick="showUserMenu(${user.id}, event)">⋮</button>
                </div>
            `;
            return userDiv;
        }
        
        async function loadMessages() {
            const response = await fetch(`/api/messages?room=${currentRoom}`);
            const messages = await response.json();
            
            const messagesDiv = document.getElementById('messages');
            messagesDiv.innerHTML = '';
            
            messages.forEach(msg => addMessage(msg, false));
            scrollToBottom();
        }
        
        function addMessage(data, scroll = true) {
            const messagesDiv = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${data.user_id === currentUserId ? 'message-own' : 'message-other'}`;
            
            const time = new Date(data.created_at || data.timestamp).toLocaleTimeString();
            
            messageDiv.innerHTML = `
                <div class="message-content">
                    <div class="message-info">
                        <span class="message-username">${data.username}</span>
                        <span class="message-time">${time}</span>
                    </div>
                    <div>${escapeHtml(data.message)}</div>
                </div>
            `;
            
            messagesDiv.appendChild(messageDiv);
            if (scroll) scrollToBottom();
        }
        
        function addSystemMessage(message) {
            const messagesDiv = document.getElementById('messages');
            const systemDiv = document.createElement('div');
            systemDiv.className = 'message';
            systemDiv.style.justifyContent = 'center';
            systemDiv.innerHTML = `
                <div style="background: #e0e0e0; padding: 5px 15px; border-radius: 20px; font-size: 12px; color: #666;">
                    ${message}
                </div>
            `;
            messagesDiv.appendChild(systemDiv);
            scrollToBottom();
        }
        
        function sendMessage() {
            const input = document.getElementById('message-input');
            const message = input.value.trim();
            
            if (message) {
                socket.emit('send_message', {
                    message: message,
                    room: currentRoom,
                    is_private: false
                });
                input.value = '';
                hideTyping();
            }
        }
        
        function switchRoom(room) {
            if (room === currentRoom) return;
            
            socket.emit('leave_room', {room: currentRoom});
            currentRoom = room;
            socket.emit('join_room', {room: currentRoom});
            
            document.getElementById('current-room').textContent = room;
            loadMessages();
            
            // Обновляем активную комнату в списке
            document.querySelectorAll('.room-item').forEach(item => {
                item.classList.remove('active');
                if (item.textContent.includes(room)) {
                    item.classList.add('active');
                }
            });
        }
        
        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            } else {
                showTyping();
            }
        }
        
        function showTyping() {
            socket.emit('typing', {
                room: currentRoom,
                is_typing: true
            });
            
            if (typingTimeout) clearTimeout(typingTimeout);
            typingTimeout = setTimeout(() => {
                hideTyping();
            }, 1000);
        }
        
        function hideTyping() {
            socket.emit('typing', {
                room: currentRoom,
                is_typing: false
            });
        }
        
        function showTypingIndicator(data) {
            const indicator = document.getElementById('typing-indicator');
            if (data.is_typing) {
                indicator.textContent = `${data.username} печатает...`;
                setTimeout(() => {
                    if (indicator.textContent === `${data.username} печатает...`) {
                        indicator.textContent = '';
                    }
                }, 2000);
            } else {
                indicator.textContent = '';
            }
        }
        
        function switchSection(section) {
            const roomsSection = document.getElementById('rooms-section');
            const usersSection = document.getElementById('users-section');
            const buttons = document.querySelectorAll('.nav-btn');
            
            if (section === 'rooms') {
                roomsSection.style.display = 'block';
                usersSection.style.display = 'none';
                buttons[0].classList.add('active');
                buttons[1].classList.remove('active');
            } else {
                roomsSection.style.display = 'none';
                usersSection.style.display = 'block';
                buttons[0].classList.remove('active');
                buttons[1].classList.add('active');
            }
        }
        
        function showCreateRoomModal() {
            document.getElementById('create-room-modal').style.display = 'flex';
        }
        
        function closeModal(modalId) {
            document.getElementById(modalId).style.display = 'none';
        }
        
        async function createRoom() {
            const name = document.getElementById('room-name').value;
            const description = document.getElementById('room-description').value;
            const isPrivate = document.getElementById('room-private').checked;
            const password = document.getElementById('room-password').value;
            
            if (!name) {
                alert('Введите название комнаты');
                return;
            }
            
            const response = await fetch('/api/create_room', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, description, is_private: isPrivate, password})
            });
            
            const data = await response.json();
            if (data.success) {
                closeModal('create-room-modal');
                await loadRooms();
                switchRoom(name);
            } else {
                alert(data.error);
            }
        }
        
        function startPrivateChat(userId, username) {
            currentPrivateChat = userId;
            document.getElementById('current-room').textContent = `Приватный чат с ${username}`;
            // Здесь можно загрузить историю приватных сообщений
        }
        
        function showUserMenu(userId, event) {
            selectedUserId = userId;
            const menu = document.getElementById('context-menu');
            menu.style.display = 'block';
            menu.style.left = event.pageX + 'px';
            menu.style.top = event.pageY + 'px';
            
            setTimeout(() => {
                document.addEventListener('click', () => {
                    menu.style.display = 'none';
                }, {once: true});
            }, 100);
        }
        
        async function blockUser() {
            if (selectedUserId) {
                await fetch('/api/block_user', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({user_id: selectedUserId})
                });
                alert('Пользователь заблокирован');
                loadUsers();
            }
        }
        
        function addPrivateMessageNotification(data) {
            addSystemMessage(`Приватное сообщение от ${data.from_username}: ${data.message}`);
        }
        
        function scrollToBottom() {
            const messagesDiv = document.getElementById('messages');
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        async function logout() {
            await fetch('/logout');
            window.location.href = '/';
        }
        
        // Получение ID текущего пользователя
        let currentUserId = null;
        async function getCurrentUserId() {
            const response = await fetch('/api/current-user-id');
            const data = await response.json();
            currentUserId = data.id;
        }
        
        // Обработка приватных комнат
        document.getElementById('room-private').addEventListener('change', (e) => {
            const passwordInput = document.getElementById('room-password');
            passwordInput.style.display = e.target.checked ? 'block' : 'none';
        });
        
        // Запуск приложения
        getCurrentUserId();
        init();
    </script>
</body>
</html>
    ''')

# Добавляем маршрут для получения текущего пользователя
@app.route('/api/current-user-id')
@login_required
def get_current_user_id():
    return jsonify({'id': current_user.id})

@app.route('/api/current-user')
@login_required
def get_current_user():
    with get_db() as conn:
        user = conn.execute('SELECT id, username, is_admin FROM users WHERE id = ?', (current_user.id,)).fetchone()
        return jsonify(dict(user))

if __name__ == '__main__':
    # Запуск приложения
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
