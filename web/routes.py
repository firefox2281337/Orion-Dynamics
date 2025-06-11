# web/routes.py
"""
Главный модуль инициализации Flask приложения и регистрации Blueprint'ов
"""

from flask import Flask
from core.config.logger_config import setup_logger

# Импорт всех Blueprint'ов
from web.blueprints.main_routes import main_bp
from web.blueprints.nexus_routes import nexus_bp
from web.blueprints.api_routes import api_bp
from web.blueprints.sql_routes import sql_bp
from web.blueprints.file_routes import file_bp
from web.blueprints.processing_routes import processing_bp
from web.blueprints.admin_routes import admin_bp
from web.blueprints.admin_auth import auth_bp
from web.blueprints.registry_routes import registry_bp
from web.blueprints.lost_contracts_routes import lost_contracts_bp
from web.blueprints.jarvis_routes import jarvis_bp
from web.blueprints.campaigns_routes import campaigns_bp

def init_app(app: Flask, log_signal_emitter):
    """
    Инициализирует Flask-приложение и регистрирует все Blueprint'ы
    
    Args:
        app: Flask приложение
        log_signal_emitter: Объект для отправки сигналов логирования
    """
    
    logger = setup_logger()

    @app.route('/debug/routes')
    def debug_routes():
        """Показать все доступные маршруты"""
        routes = []
        for rule in app.url_map.iter_rules():
            methods = ','.join(rule.methods - {'OPTIONS', 'HEAD'})
            routes.append(f"{rule.rule} [{methods}] -> {rule.endpoint}")
        return '<br>'.join(routes)
    
    # Регистрируем все Blueprint'ы
    app.register_blueprint(main_bp)
    app.register_blueprint(nexus_bp, url_prefix='/nexus')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(sql_bp, url_prefix='/sql')
    app.register_blueprint(file_bp, url_prefix='/files')
    app.register_blueprint(processing_bp, url_prefix='/processing')
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(registry_bp)
    app.register_blueprint(lost_contracts_bp)
    app.register_blueprint(jarvis_bp)
    app.register_blueprint(campaigns_bp)
    
    # Сохраняем log_signal_emitter в конфигурации приложения
    app.config['LOG_SIGNAL_EMITTER'] = log_signal_emitter
    
    logger.info("Flask приложение инициализировано со всеми Blueprint'ами включая админ панель")

# Глобальная переменная для задачи обработки (будет перенесена в отдельный модуль)
from web.blueprints.processing import ProcessingTask
current_task = ProcessingTask()