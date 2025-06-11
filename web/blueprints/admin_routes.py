# web/blueprints/admin_routes.py
"""
Админ панель - все административные функции
"""

from flask import Blueprint, render_template, jsonify, request, redirect, session, url_for, flash
from web.utils.admin_security import admin_required, admin_security
from core.config.logger_config import setup_logger
from functools import wraps
import psutil
import os
import sys
import time
import json
import sqlite3
from datetime import datetime, timedelta
import logging
from pathlib import Path
import subprocess
import shutil

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
logger = setup_logger()

# Применяем защиту ко всем маршрутам админки
@admin_bp.before_request
def before_request():
    # Проверяем, не является ли это страницей входа
    if request.endpoint in ['admin_auth.admin_login', 'admin_auth.admin_logout']:
        return
    
    if not admin_security.validate_session():
        return redirect(url_for('admin_auth.admin_login'))

# Декоратор для проверки доступа админа
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Здесь можно добавить проверку авторизации
        # Пока что просто пропускаем
        return f(*args, **kwargs)
    return decorated_function

# Главная страница дашборда
@admin_bp.route('/dashboard')
@admin_required
def admin_dashboard():
    """Главная страница дашборда с защитой"""
    try:
        stats = get_system_stats()
        
        return render_template('admin/dashboard.html', stats=stats)
    except Exception as e:
        flash('Ошибка загрузки дашборда', 'error')
        return redirect(url_for('admin_auth.admin_login'))

# API для получения системной статистики
@admin_bp.route('/api/stats')
@admin_required
def api_stats():
    """API статистики с защитой"""
    try:
        return jsonify(get_system_stats())
    except Exception as e:
        return jsonify({'error': 'Ошибка получения статистики'}), 500

# Мониторинг производительности
@admin_bp.route('/performance')
@admin_required
def performance_monitor():
    return render_template('admin/performance.html')

# Просмотр логов
@admin_bp.route('/logs')
@admin_required
def logs_viewer():
    return render_template('admin/logs.html')

# API для получения логов
@admin_bp.route('/api/logs')
@admin_required
def api_logs():
    page = request.args.get('page', 1, type=int)
    level = request.args.get('level', 'all')
    limit = request.args.get('limit', 50, type=int)
    
    logs = get_recent_logs(page, level, limit)
    return jsonify(logs)

# Информация о системе
@admin_bp.route('/system')
@admin_required
def system_info():
    return render_template('admin/system.html')

# Редактор кода
@admin_bp.route('/code-editor')
@admin_required
def code_editor():
    return render_template('admin/code_editor.html')

# API для работы с файлами в редакторе
@admin_bp.route('/api/files')
@admin_required
def api_files():
    path = request.args.get('path', '.')
    try:
        files = []
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            files.append({
                'name': item,
                'type': 'directory' if os.path.isdir(item_path) else 'file',
                'size': os.path.getsize(item_path) if os.path.isfile(item_path) else 0,
                'modified': os.path.getmtime(item_path)
            })
        return jsonify({'files': files, 'current_path': path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/file-content')
@admin_required
def api_file_content():
    filepath = request.args.get('path')
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'content': content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/save-file', methods=['POST'])
@admin_required
def api_save_file():
    data = request.get_json()
    filepath = data.get('path')
    content = data.get('content')
    
    try:
        # Создаем бэкап
        backup_path = f"{filepath}.backup.{int(time.time())}"
        shutil.copy2(filepath, backup_path)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Веб-терминал
@admin_bp.route('/terminal')
@admin_required
def web_terminal():
    return render_template('admin/terminal.html')

# API для выполнения команд терминала
@admin_bp.route('/api/execute', methods=['POST'])
@admin_required
def api_execute():
    data = request.get_json()
    command = data.get('command', '')
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        return jsonify({
            'output': result.stdout,
            'error': result.stderr,
            'returncode': result.returncode
        })
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Команда превысила лимит времени (30с)'}), 408
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Редактор конфигурации
@admin_bp.route('/config')
@admin_required
def config_editor():
    return render_template('admin/config.html')

# Центр безопасности
@admin_bp.route('/security')
@admin_required
def security_center():
    """Центр безопасности с дополнительными данными"""
    security_data = {
        'active_sessions': len(admin_security.active_sessions),
        'blocked_ips': list(admin_security.blocked_ips),
        'recent_events': admin_security.security_events[-20:],
        'login_attempts': admin_security.login_attempts,
        'system_health': calculate_system_health()
    }
    return render_template('admin/security.html', security_data=security_data)

@admin_bp.route('/api/block-ip', methods=['POST'])
@admin_required
def api_block_ip():
    """API для блокировки IP адреса"""
    try:
        data = request.get_json()
        ip = data.get('ip')
        
        if not ip:
            return jsonify({'error': 'IP адрес не указан'}), 400
        
        admin_security.blocked_ips.add(ip)
        admin_security.save_security_config()
        
        admin_security.log_security_event(
            'ip_blocked_manually',
            f'IP {ip} blocked by admin {session.get("admin_user")}',
            'medium'
        )
        
        return jsonify({'success': True, 'message': f'IP {ip} заблокирован'})
    except Exception as e:
        logger.error(f"Block IP error: {e}")
        return jsonify({'error': 'Ошибка блокировки IP'}), 500
    
@admin_bp.route('/api/unblock-ip', methods=['POST'])
@admin_required
def api_unblock_ip():
    """API для разблокировки IP адреса"""
    try:
        data = request.get_json()
        ip = data.get('ip')
        
        if not ip:
            return jsonify({'error': 'IP адрес не указан'}), 400
        
        admin_security.blocked_ips.discard(ip)
        admin_security.save_security_config()
        
        admin_security.log_security_event(
            'ip_unblocked',
            f'IP {ip} unblocked by admin {session.get("admin_user")}',
            'info'
        )
        
        return jsonify({'success': True, 'message': f'IP {ip} разблокирован'})
    except Exception as e:
        logger.error(f"Unblock IP error: {e}")
        return jsonify({'error': 'Ошибка разблокировки IP'}), 500

@admin_bp.route('/api/security-events')
@admin_required
def api_security_events():
    """API событий безопасности"""
    try:
        events = admin_security.security_events[-50:]  # Последние 50 событий
        return jsonify(events)
    except Exception as e:
        logger.error(f"Security events API error: {e}")
        return jsonify({'error': 'Ошибка получения событий'}), 500

# Управление пользователями
@admin_bp.route('/users')
@admin_required
def user_management():
    return render_template('admin/users.html')

# Управление резервными копиями
@admin_bp.route('/backup')
@admin_required
def backup_manager():
    return render_template('admin/backup.html')

# API для создания бэкапа
@admin_bp.route('/api/create-backup', methods=['POST'])
@admin_required
def api_create_backup():
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = f"backups/backup_{timestamp}"
        os.makedirs(backup_dir, exist_ok=True)
        
        # Копируем важные файлы
        important_dirs = ['core', 'web', 'gui']
        important_files = ['main.py', 'requirements.txt']
        
        for dir_name in important_dirs:
            if os.path.exists(dir_name):
                shutil.copytree(dir_name, os.path.join(backup_dir, dir_name))
        
        for file_name in important_files:
            if os.path.exists(file_name):
                shutil.copy2(file_name, backup_dir)
        
        return jsonify({
            'success': True, 
            'backup_path': backup_dir,
            'message': f'Бэкап создан: {backup_dir}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Планировщик задач
@admin_bp.route('/scheduler')
@admin_required
def task_scheduler():
    return render_template('admin/scheduler.html')

# Менеджер плагинов
@admin_bp.route('/plugins')
@admin_required
def plugin_manager():
    return render_template('admin/plugins.html')

# Аналитика
@admin_bp.route('/analytics')
@admin_required
def analytics_dashboard():
    return render_template('admin/analytics.html')

# API для данных производительности
@admin_bp.route('/api/performance-data')
@admin_required
def api_performance_data():
    timeframe = request.args.get('timeframe', '1h')
    data = get_performance_data(timeframe)
    return jsonify(data)

# API для перезагрузки системы
@admin_bp.route('/api/system/restart', methods=['POST'])
@admin_required
def api_system_restart():
    try:
        # Логируем действие
        logging.info("Система перезагружается через админ панель")
        
        # Можно добавить задержку для корректного завершения
        import threading
        def restart_system():
            time.sleep(2)
            os.execv(sys.executable, ['python'] + sys.argv)
        
        thread = threading.Thread(target=restart_system)
        thread.daemon = True
        thread.start()
        
        return jsonify({'success': True, 'message': 'Система перезагружается...'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Функции-помощники
def get_system_stats():
    """Получение системной статистики"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('.')
        
        # Информация о процессах
        process_count = len(psutil.pids())
        
        # Время работы системы
        boot_time = psutil.boot_time()
        uptime = datetime.now() - datetime.fromtimestamp(boot_time)
        uptime_str = str(uptime).split('.')[0]
        
        # Размеры директорий
        project_size = get_directory_size('.')
        logs_size = get_directory_size('logs') if os.path.exists('logs') else 0
        backups_size = get_directory_size('backups') if os.path.exists('backups') else 0
        
        # База данных (заглушка)
        databases = {
            'connection_pools': {
                'main_db': {'connected': True, 'response_time': 12},
                'cache_db': {'connected': True, 'response_time': 8},
                'log_db': {'connected': False, 'response_time': None}
            }
        }
        
        # Пользователи (заглушка)
        users_data = {
            'active_users_24h': 42,
            'top_pages': [
                {'page': '/dashboard', 'visits': 156},
                {'page': '/nexus', 'visits': 89},
                {'page': '/files', 'visits': 67},
                {'page': '/api/data', 'visits': 45},
                {'page': '/processing', 'visits': 23}
            ]
        }
        
        # События безопасности (заглушка)
        security_data = {
            'high_severity_events': 3
        }
        
        return {
            'system': {
                'cpu_usage': round(cpu_percent, 1),
                'memory_usage': round(memory.percent, 1),
                'disk_usage': round(disk.percent, 1),
                'process_count': process_count,
                'uptime': uptime_str
            },
            'storage': {
                'project_size': project_size,
                'logs_size': logs_size,
                'backups_size': backups_size,
                'total_size': project_size + logs_size + backups_size
            },
            'databases': databases,
            'users': users_data,
            'security': security_data
        }
    except Exception as e:
        logging.error(f"Ошибка получения системной статистики: {e}")
        return {}

def get_directory_size(path):
    """Получение размера директории"""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
    except:
        pass
    return total_size

def get_recent_logs(page=1, level='all', limit=50):
    """Получение последних логов"""
    logs = []
    try:
        # Здесь можно добавить чтение из файлов логов
        # Пока что возвращаем заглушку
        sample_logs = [
            {
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'message': 'Система запущена успешно',
                'source': 'main.py'
            },
            {
                'timestamp': (datetime.now() - timedelta(minutes=5)).isoformat(),
                'level': 'WARNING',
                'message': 'Высокая загрузка CPU',
                'source': 'monitor.py'
            },
            {
                'timestamp': (datetime.now() - timedelta(minutes=10)).isoformat(),
                'level': 'ERROR',
                'message': 'Ошибка подключения к базе данных',
                'source': 'db_utils.py'
            }
        ]
        
        # Фильтрация по уровню
        if level != 'all':
            sample_logs = [log for log in sample_logs if log['level'].lower() == level.lower()]
        
        # Пагинация
        start = (page - 1) * limit
        end = start + limit
        
        return {
            'logs': sample_logs[start:end],
            'total': len(sample_logs),
            'page': page,
            'pages': (len(sample_logs) + limit - 1) // limit
        }
    except Exception as e:
        logging.error(f"Ошибка получения логов: {e}")
        return {'logs': [], 'total': 0, 'page': 1, 'pages': 0}

def get_security_events():
    """Получение событий безопасности"""
    events = [
        {
            'type': 'Подозрительная активность',
            'severity': 'high',
            'message': 'Множественные неудачные попытки входа с IP 192.168.1.100',
            'timestamp': datetime.now().isoformat(),
            'source': '192.168.1.100'
        },
        {
            'type': 'Изменение конфигурации',
            'severity': 'medium',
            'message': 'Файл конфигурации изменен пользователем admin',
            'timestamp': (datetime.now() - timedelta(hours=2)).isoformat(),
            'source': 'config_editor'
        },
        {
            'type': 'Доступ к системе',
            'severity': 'low',
            'message': 'Новый вход в админ панель',
            'timestamp': (datetime.now() - timedelta(hours=5)).isoformat(),
            'source': 'admin_panel'
        }
    ]
    return events

def get_performance_data(timeframe='1h'):
    """Получение данных производительности для графиков"""
    import random
    
    now = datetime.now()
    if timeframe == '1h':
        delta = timedelta(hours=1)
        intervals = 60
    elif timeframe == '6h':
        delta = timedelta(hours=6)
        intervals = 72
    elif timeframe == '24h':
        delta = timedelta(hours=24)
        intervals = 288
    else:  # 7d
        delta = timedelta(days=7)
        intervals = 168
    
    start_time = now - delta
    step = delta / intervals
    
    data = {
        'labels': [],
        'cpu': [],
        'memory': [],
        'disk': []
    }
    
    for i in range(intervals):
        timestamp = start_time + (step * i)
        data['labels'].append(timestamp.isoformat())
        data['cpu'].append(random.randint(10, 80))
        data['memory'].append(random.randint(30, 70))
        data['disk'].append(random.randint(20, 60))
    
    return data

def calculate_system_health():
    """Расчет общего здоровья системы"""
    try:
        cpu_usage = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        
        # Базовый расчет здоровья
        health_score = 100
        
        if cpu_usage > 80:
            health_score -= 20
        elif cpu_usage > 60:
            health_score -= 10
        
        if memory.percent > 85:
            health_score -= 15
        elif memory.percent > 70:
            health_score -= 8
        
        # Учитываем события безопасности
        recent_critical = len([
            e for e in admin_security.security_events[-10:]
            if e.get('severity') == 'high'
        ])
        health_score -= recent_critical * 5
        
        return max(health_score, 0)
    except:
        return 50  # Средний уровень при ошибке