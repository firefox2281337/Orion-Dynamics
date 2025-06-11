# web/utils/access_control.py
"""
Модуль контроля доступа
"""

from functools import wraps
from datetime import datetime
from flask import request, render_template
from core.config.db_config import ALLOWED_IPS
from web.utils.logging_helper import log_user_access


def require_ip_access(f):
    """
    Декоратор для проверки IP адреса
    
    Args:
        f: Функция-обработчик маршрута
        
    Returns:
        Обёрнутая функция с проверкой доступа
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.remote_addr
        current_time = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
        
        if client_ip not in ALLOWED_IPS:
            log_user_access(
                page="restricted",
                client_ip=client_ip,
                current_time=current_time,
                message="Пользователь без доступа попытался зайти на защищённую страницу",
                level="WARNING"
            )
            return render_template('site/error.html', remote_addr=client_ip), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


def check_ip_access(client_ip):
    """
    Проверка доступа по IP
    
    Args:
        client_ip: IP адрес для проверки
        
    Returns:
        bool: True если доступ разрешён
    """
    return client_ip in ALLOWED_IPS


def log_access_attempt(client_ip, page, success=True):
    """
    Логирование попытки доступа
    
    Args:
        client_ip: IP адрес
        page: Страница
        success: Успешность доступа
    """
    current_time = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
    
    if success:
        message = f"Успешный доступ к {page}"
        level = "INFO"
    else:
        message = f"Отказ в доступе к {page}"
        level = "WARNING"
    
    log_user_access(
        page=page,
        client_ip=client_ip,
        current_time=current_time,
        message=message,
        level=level
    )