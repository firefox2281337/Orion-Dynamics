import sys
import os
import json
import signal
from flask import Flask
from web import routes
from core.config.logger_config import setup_logger
from core.config.db_config import SECRET_KEY, DATA_PATH, FILES_DIR
from pathlib import Path

logger = setup_logger()

app = Flask(__name__, template_folder='web/templates', static_folder='web/static')
app.config['SECRET_KEY'] = SECRET_KEY

def setup_directories():
    """Создание необходимых директорий"""
    directories = [
    "temp_uploads",
    FILES_DIR,
    os.path.dirname(DATA_PATH)
    ]

    for directory in directories:
        Path(directory).mkdir(exist_ok=True)

    logger.info("Директории созданы успешно")


def signal_handler(sig, frame):
    """Обработчик сигналов для корректного завершения"""
    logger.info("Получен сигнал завершения")
    sys.exit(0)

def main():
    """Главная функция приложения"""

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    setup_directories()

    routes.init_app(app, log_signal_emitter=None)

    logger.info("Запуск веб-сервера...")

    try:
        app.run(
            host='192.168.50.220', 
            port=5000, 
            debug=False, 
            use_reloader=False, 
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("Приложение остановлено пользователем")
    except Exception as e:
        logger.error(f"Ошибка при запуске приложения: {e}")
        sys.exit(1)

    logger.info("Приложение завершено")

if __name__ == "__main__":
    main()