# web/routes/registry_routes.py
"""
Маршруты для обработки реестра сделок
"""

from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
from pathlib import Path
import os
import re

from web.services.registry_service import RegistryService

# Создаем blueprint
registry_bp = Blueprint('registry', __name__, url_prefix='/registry')

# Инициализируем сервис
registry_service = RegistryService()

ALLOWED_EXTENSIONS = {'xls', 'xlsx'}


def allowed_file(filename):
    """Проверка допустимого расширения файла"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def safe_filename(filename):
    """
    Безопасное имя файла с сохранением кириллицы для проверки типа
    """
    # Убираем опасные символы, но оставляем кириллицу
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = filename.strip()
    return filename


@registry_bp.route('/process', methods=['POST'])
def process_files():
    """Обработка загруженных файлов"""
    try:
        # Проверяем наличие файлов
        if 'files' not in request.files:
            return jsonify({'error': 'Файлы не найдены'}), 400
        
        files = request.files.getlist('files')
        
        if len(files) < 3:
            return jsonify({'error': 'Необходимо загрузить минимум 3 файла'}), 400
        
        # Разделяем файлы по типам
        deals_file = None
        check_file = None
        employee_file = None
        
        for file in files:
            if file.filename == '':
                continue
                
            if not allowed_file(file.filename):
                continue
            
            # Используем оригинальное имя для проверки типа
            original_filename = file.filename
            print(f"Оригинальное имя файла: {original_filename}")
            
            # Определяем тип файла по оригинальному имени
            if original_filename.startswith('Сделки'):
                deals_file = file
                print("Найден файл сделок")
            elif original_filename.startswith('Проверка'):
                check_file = file
                print("Найден файл проверки")
            elif original_filename.startswith('empl'):
                employee_file = file
                print("Найден файл сотрудников")
            else:
                print(f"Неопознанный файл: {original_filename}")
        
        # Проверяем что все необходимые файлы присутствуют
        if not deals_file:
            return jsonify({'error': 'Не найден файл сделок (должен начинаться с "Сделки")'}), 400
        
        if not check_file:
            return jsonify({'error': 'Не найден файл проверки (должен начинаться с "Проверка")'}), 400
            
        if not employee_file:
            return jsonify({'error': 'Не найден файл сотрудников (должен начинаться с "empl")'}), 400
        
        print("Все файлы найдены, запускаем обработку...")
        
        # Запускаем обработку
        success, message = registry_service.process_files(deals_file, check_file, employee_file)
        
        if success:
            return jsonify({'message': message})
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        print(f"Ошибка в process_files: {str(e)}")
        return jsonify({'error': str(e)}), 500


@registry_bp.route('/status', methods=['GET'])
def get_status():
    """Получение статуса обработки"""
    try:
        status = registry_service.get_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@registry_bp.route('/cancel', methods=['POST'])
def cancel_processing():
    """Отмена обработки"""
    try:
        result = registry_service.cancel_processing()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@registry_bp.route('/download', methods=['GET'])
def download_result():
    """Скачивание результата"""
    try:
        result_file = registry_service.get_result_file()
        
        if not result_file or not os.path.exists(result_file):
            return jsonify({'error': 'Файл результата не найден'}), 404
        
        return send_file(
            result_file,
            as_attachment=True,
            download_name=Path(result_file).name
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500