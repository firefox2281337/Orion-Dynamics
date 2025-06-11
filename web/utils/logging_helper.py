# web/utils/logging_helper.py
"""
Вспомогательный модуль для логирования
"""

import hashlib
from flask import current_app
from core.config.logger_config import setup_logger


def log_user_access(page, client_ip, current_time, message, level="INFO"):
    """
    Логирует доступ пользователя к странице
    
    Args:
        page: Название страницы
        client_ip: IP адрес клиента
        current_time: Время доступа
        message: Сообщение для лога
        level: Уровень логирования
    """
    logger = setup_logger()
    
    log_message = f"""
    {message}:
        ВРЕМЯ: {current_time}
        IP-адрес: {client_ip}"""
    
    # Логируем в зависимости от уровня
    if level == "INFO":
        logger.info(log_message)
    elif level == "WARNING":
        logger.warning(log_message)
    elif level == "ERROR":
        logger.error(log_message)
    
    # Отправляем сигнал, если доступен
    try:
        log_signal_emitter = current_app.config.get('LOG_SIGNAL_EMITTER')
        if log_signal_emitter:
            log_signal_emitter.log_signal.emit(log_message, level)
    except Exception:
        # Игнорируем ошибки отправки сигналов
        pass


def log_query_info(client_ip, current_time, data, sql_query=None, database=None, rows_count=None, error=None):
    """
    Логирует информацию о SQL запросе
    
    Args:
        client_ip: IP адрес клиента
        current_time: Время запроса
        data: Данные запроса
        sql_query: SQL запрос
        database: База данных
        rows_count: Количество строк в результате
        error: Ошибка (если есть)
    """
    logger = setup_logger()
    
    if sql_query:
        sql_hash = hashlib.md5(sql_query.encode('utf-8')).hexdigest()
        log_message = f"""
        Входящий запрос:
            ВРЕМЯ: {current_time}
            IP-адрес: {client_ip}
            БД: {database}
            Запрос: {sql_hash}"""
        
        if rows_count is not None:
            log_message += f"\n            Строк получено: {rows_count}"
        
        if error:
            log_message += f"\n            Ошибка: {error}"
            logger.error(log_message)
            level = "ERROR"
        else:
            logger.info(log_message)
            level = "INFO"
    else:
        log_message = f"""
        Запрос к API:
            ВРЕМЯ: {current_time}
            IP-адрес: {client_ip}
            Данные: {str(data)[:100]}..."""
        logger.info(log_message)
        level = "INFO"
    
    # Отправляем сигнал
    try:
        log_signal_emitter = current_app.config.get('LOG_SIGNAL_EMITTER')
        if log_signal_emitter:
            log_signal_emitter.log_signal.emit(log_message, level)
    except Exception:
        pass


def log_error(message, client_ip=None, traceback_info=None):
    """
    Логирует ошибку
    
    Args:
        message: Сообщение об ошибке
        client_ip: IP адрес клиента (опционально)
        traceback_info: Информация о трассировке (опционально)
    """
    logger = setup_logger()
    
    log_message = f"Ошибка: {message}"
    if client_ip:
        log_message += f"\nIP-адрес: {client_ip}"
    if traceback_info:
        log_message += f"\nТрассировка: {traceback_info}"
    
    logger.error(log_message)
    
    try:
        log_signal_emitter = current_app.config.get('LOG_SIGNAL_EMITTER')
        if log_signal_emitter:
            log_signal_emitter.log_signal.emit(log_message, "ERROR")
    except Exception:
        pass


def setup_simple_logger():
    """Настройка простого логгера"""
    import logging
    
    # Создаем простой логгер
    logger = logging.getLogger('admin_panel')
    logger.setLevel(logging.INFO)
    
    # Консольный обработчик
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger