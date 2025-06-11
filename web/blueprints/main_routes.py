# web/blueprints/main_routes.py
"""
Blueprint для основных маршрутов приложения
"""

import threading
import time
from datetime import datetime, timedelta
from flask import jsonify
from flask import Blueprint, render_template, request, send_from_directory
from core.config.db_config import DATABASES
from core.database.db_utils import check_database_status
from core.utils.helpers import get_server_uptime, get_cpu_usage, get_memory_usage, get_disk_usage
from web.utils.logging_helper import log_user_access

cached_data = {
    "system_info": {},
    "db_statuses": {},
    "last_update": None
}
cache_lock = threading.Lock()
CACHE_DURATION = 30

def update_cache_background():
    """Фоновое обновление кэша"""
    global cached_data
    
    while True:
        try:
            # Получаем свежие данные
            system_info = {
                "uptime": get_server_uptime(),
                "cpu": get_cpu_usage(),
                "memory": get_memory_usage(),
                "disk": get_disk_usage()
            }
            
            db_statuses = {}
            for db_name, config in DATABASES.items():
                db_statuses[db_name] = check_database_status(config)
            
            # Обновляем кэш потокобезопасно
            with cache_lock:
                cached_data["system_info"] = system_info
                cached_data["db_statuses"] = db_statuses
                cached_data["last_update"] = datetime.now()
                
        except Exception as e:
            print(f"Ошибка обновления кэша: {e}")
        
        time.sleep(CACHE_DURATION)

cache_thread = threading.Thread(target=update_cache_background, daemon=True)
cache_thread.start()

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def server_status():
    """Главная страница с информацией о статусе сервера - быстрая версия"""
    client_ip = request.remote_addr
    current_time = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
    
    # Используем кэшированные данные
    with cache_lock:
        system_info = cached_data["system_info"].copy()
        db_statuses = cached_data["db_statuses"].copy()
        last_update = cached_data["last_update"]
    
    # Форматируем время последнего обновления
    if last_update:
        last_check = last_update.strftime("%d.%m.%Y %H:%M:%S")
    else:
        last_check = "Загрузка..."
    
    # Логируем доступ (можно вынести в отдельный поток)
    threading.Thread(
        target=log_user_access,
        args=("site/index.html", client_ip, current_time, "Пользователь зашёл на index.html"),
        daemon=True
    ).start()
    
    return render_template(
        'site/index.html',
        system_info=system_info,
        db_statuses=db_statuses,
        last_check=last_check
    )


@main_bp.route('/server.ico')
def favicon():
    """Возвращает иконку сервера"""
    return send_from_directory('static', 'server.ico', mimetype='image/x-icon')