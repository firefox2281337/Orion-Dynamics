# web/utils/admin_security.py
"""
Система безопасности админ панели
Многоуровневая защита доступа
"""

from functools import wraps
from flask import request, session, redirect, url_for, abort, current_app
import hashlib
import secrets
import time
import json
import os
from datetime import datetime, timedelta
import ipaddress
import logging

logger = logging.getLogger(__name__)

class AdminSecurity:
    def __init__(self):
        self.login_attempts = {}  # IP -> {attempts: int, last_attempt: timestamp, blocked_until: timestamp}
        self.active_sessions = {}  # session_id -> {user: str, ip: str, created: timestamp, last_activity: timestamp}
        self.allowed_ips = set()  # Белый список IP адресов
        self.blocked_ips = set()  # Черный список IP адресов
        self.security_events = []  # Лог событий безопасности
        
        # Настройки безопасности
        self.MAX_LOGIN_ATTEMPTS = 5
        self.BLOCK_DURATION = 900  # 15 минут блокировки
        self.SESSION_TIMEOUT = 3600  # 1 час таймаут сессии
        self.ADMIN_SECRET_KEY = os.environ.get('ADMIN_SECRET_KEY', 'change-me-in-production')
        
        # Загружаем настройки из файла
        self.load_security_config()
    
    def load_security_config(self):
        """Загрузка конфигурации безопасности"""
        try:
            config_path = 'security_config.json'
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.allowed_ips = set(config.get('allowed_ips', []))
                    self.blocked_ips = set(config.get('blocked_ips', []))
                    logger.info("Security configuration loaded")
        except Exception as e:
            logger.error(f"Error loading security config: {e}")
    
    def save_security_config(self):
        """Сохранение конфигурации безопасности"""
        try:
            config = {
                'allowed_ips': list(self.allowed_ips),
                'blocked_ips': list(self.blocked_ips),
                'updated': datetime.now().isoformat()
            }
            with open('security_config.json', 'w') as f:
                json.dump(config, f, indent=2)
            logger.info("Security configuration saved")
        except Exception as e:
            logger.error(f"Error saving security config: {e}")
    
    def log_security_event(self, event_type, message, severity='info', ip=None):
        """Логирование событий безопасности"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'message': message,
            'severity': severity,
            'ip': ip or request.remote_addr,
            'user_agent': request.headers.get('User-Agent', 'Unknown')
        }
        self.security_events.append(event)
        
        # Оставляем только последние 1000 событий
        if len(self.security_events) > 1000:
            self.security_events = self.security_events[-1000:]
        
        # Логируем в файл
        logger.info(f"Security Event: {event_type} - {message} (IP: {event['ip']})")
    
    def get_client_ip(self):
        """Получение реального IP клиента"""
        # Проверяем заголовки прокси
        forwarded_ips = request.headers.get('X-Forwarded-For')
        if forwarded_ips:
            return forwarded_ips.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return request.remote_addr
    
    def is_ip_blocked(self, ip):
        """Проверка, заблокирован ли IP"""
        current_time = time.time()
        
        # Проверяем черный список
        if ip in self.blocked_ips:
            return True
        
        # Проверяем временную блокировку за превышение попыток входа
        if ip in self.login_attempts:
            attempt_data = self.login_attempts[ip]
            if 'blocked_until' in attempt_data and current_time < attempt_data['blocked_until']:
                return True
        
        return False
    
    def is_ip_allowed(self, ip):
        """Проверка, разрешен ли IP (если используется белый список)"""
        if not self.allowed_ips:  # Если белый список пуст, разрешаем всем
            return True
        return ip in self.allowed_ips
    
    def record_login_attempt(self, ip, success=False, username=None):
        """Запись попытки входа"""
        current_time = time.time()
        
        if ip not in self.login_attempts:
            self.login_attempts[ip] = {'attempts': 0, 'last_attempt': current_time}
        
        attempt_data = self.login_attempts[ip]
        
        if success:
            # Успешный вход - сбрасываем счетчик
            self.login_attempts[ip] = {'attempts': 0, 'last_attempt': current_time}
            self.log_security_event(
                'login_success', 
                f'Successful admin login for user: {username}', 
                'info', 
                ip
            )
        else:
            # Неудачная попытка
            attempt_data['attempts'] += 1
            attempt_data['last_attempt'] = current_time
            
            self.log_security_event(
                'login_failed', 
                f'Failed admin login attempt for user: {username}', 
                'warning', 
                ip
            )
            
            # Блокируем IP если превышено количество попыток
            if attempt_data['attempts'] >= self.MAX_LOGIN_ATTEMPTS:
                attempt_data['blocked_until'] = current_time + self.BLOCK_DURATION
                self.log_security_event(
                    'ip_blocked', 
                    f'IP blocked due to {self.MAX_LOGIN_ATTEMPTS} failed login attempts', 
                    'high', 
                    ip
                )
    
    def create_session(self, username, ip):
        """Создание безопасной сессии"""
        session_id = secrets.token_urlsafe(32)
        current_time = time.time()
        
        # Сохраняем информацию о сессии
        self.active_sessions[session_id] = {
            'user': username,
            'ip': ip,
            'created': current_time,
            'last_activity': current_time
        }
        
        # Устанавливаем сессию Flask
        session['admin_session_id'] = session_id
        session['admin_user'] = username
        session['admin_ip'] = ip
        session.permanent = True
        
        self.log_security_event(
            'session_created', 
            f'Admin session created for user: {username}', 
            'info', 
            ip
        )
        
        return session_id
    
    def validate_session(self):
        """Проверка валидности текущей сессии"""
        if 'admin_session_id' not in session:
            return False
        
        session_id = session['admin_session_id']
        current_ip = self.get_client_ip()
        current_time = time.time()
        
        # Проверяем существование сессии
        if session_id not in self.active_sessions:
            return False
        
        session_data = self.active_sessions[session_id]
        
        # Проверяем IP адрес (защита от hijacking)
        if session_data['ip'] != current_ip:
            self.log_security_event(
                'session_hijack_attempt', 
                f'Session hijack attempt detected. Original IP: {session_data["ip"]}, Current IP: {current_ip}', 
                'high', 
                current_ip
            )
            self.destroy_session(session_id)
            return False
        
        # Проверяем таймаут сессии
        if current_time - session_data['last_activity'] > self.SESSION_TIMEOUT:
            self.log_security_event(
                'session_expired', 
                f'Admin session expired for user: {session_data["user"]}', 
                'info', 
                current_ip
            )
            self.destroy_session(session_id)
            return False
        
        # Обновляем время последней активности
        session_data['last_activity'] = current_time
        
        return True
    
    def destroy_session(self, session_id=None):
        """Уничтожение сессии"""
        if session_id is None:
            session_id = session.get('admin_session_id')
        
        if session_id and session_id in self.active_sessions:
            user = self.active_sessions[session_id]['user']
            ip = self.active_sessions[session_id]['ip']
            
            del self.active_sessions[session_id]
            
            self.log_security_event(
                'session_destroyed', 
                f'Admin session destroyed for user: {user}', 
                'info', 
                ip
            )
        
        # Очищаем Flask сессию
        session.pop('admin_session_id', None)
        session.pop('admin_user', None)
        session.pop('admin_ip', None)
    
    def verify_password(self, username, password):
        """Проверка пароля администратора"""
        # В production используйте базу данных с хешированными паролями
        # Это упрощенная версия для демонстрации
        
        admin_users = {
            'admin': 'pbkdf2_sha256$260000$example$hash',  # Замените на реальные хеши
            'superuser': 'pbkdf2_sha256$260000$example$hash2'
        }
        
        # Для демонстрации - простая проверка
        # В production используйте werkzeug.security.check_password_hash
        demo_passwords = {
            'admin': 'admin123!@#',
            'superuser': 'super456!@#'
        }
        
        return username in demo_passwords and demo_passwords[username] == password
    
    def check_rate_limit(self, ip):
        """Проверка ограничения частоты запросов"""
        current_time = time.time()
        
        # Простая реализация rate limiting
        if not hasattr(self, 'request_counts'):
            self.request_counts = {}
        
        if ip not in self.request_counts:
            self.request_counts[ip] = []
        
        # Удаляем старые запросы (старше 1 минуты)
        self.request_counts[ip] = [
            req_time for req_time in self.request_counts[ip] 
            if current_time - req_time < 60
        ]
        
        # Добавляем текущий запрос
        self.request_counts[ip].append(current_time)
        
        # Проверяем лимит (максимум 100 запросов в минуту)
        if len(self.request_counts[ip]) > 100:
            self.log_security_event(
                'rate_limit_exceeded', 
                f'Rate limit exceeded: {len(self.request_counts[ip])} requests in 1 minute', 
                'high', 
                ip
            )
            return False
        
        return True
    
    def detect_suspicious_activity(self, request_data):
        """Обнаружение подозрительной активности"""
        suspicious_patterns = [
            'script>', '<iframe', 'javascript:', 'eval(',
            'union select', 'or 1=1', '../', '.env',
            'passwd', '/etc/', 'cmd.exe', 'powershell'
        ]
        
        # Проверяем URL и параметры на подозрительные паттерны
        check_strings = [
            request.url,
            str(request.args),
            str(request.form),
            request.headers.get('User-Agent', ''),
            request.headers.get('Referer', '')
        ]
        
        for check_str in check_strings:
            check_str_lower = check_str.lower()
            for pattern in suspicious_patterns:
                if pattern in check_str_lower:
                    self.log_security_event(
                        'suspicious_activity', 
                        f'Suspicious pattern detected: {pattern} in {check_str[:100]}', 
                        'high'
                    )
                    return True
        
        return False

# Создаем глобальный экземпляр
admin_security = AdminSecurity()

# Декораторы безопасности
def admin_required(f):
    """Декоратор для проверки доступа администратора"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = admin_security.get_client_ip()
        
        # Проверяем заблокирован ли IP
        if admin_security.is_ip_blocked(client_ip):
            admin_security.log_security_event(
                'blocked_access_attempt', 
                'Access attempt from blocked IP', 
                'high', 
                client_ip
            )
            abort(403)  # Forbidden
        
        # Проверяем белый список (если используется)
        if not admin_security.is_ip_allowed(client_ip):
            admin_security.log_security_event(
                'unauthorized_ip_access', 
                'Access attempt from unauthorized IP', 
                'high', 
                client_ip
            )
            abort(403)  # Forbidden
        
        # Проверяем rate limiting
        if not admin_security.check_rate_limit(client_ip):
            abort(429)  # Too Many Requests
        
        # Проверяем подозрительную активность
        if admin_security.detect_suspicious_activity(request):
            abort(403)  # Forbidden
        
        # Проверяем валидность сессии
        if not admin_security.validate_session():
            return redirect(url_for('admin.admin_login'))
        
        return f(*args, **kwargs)
    return decorated_function

def security_check(f):
    """Легкий декоратор для базовых проверок безопасности"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = admin_security.get_client_ip()
        
        # Базовые проверки
        if admin_security.is_ip_blocked(client_ip):
            abort(403)
        
        if not admin_security.check_rate_limit(client_ip):
            abort(429)
        
        return f(*args, **kwargs)
    return decorated_function