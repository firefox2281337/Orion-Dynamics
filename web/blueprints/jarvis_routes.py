# web/routes/jarvis_routes.py
"""
Маршруты для обработки Джарвиса
"""

from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
from pathlib import Path
import os

from web.services.jarvis_service import JarvisService

# Создаем blueprint
jarvis_bp = Blueprint('jarvis', __name__, url_prefix='/jarvis')

# Инициализируем сервис
jarvis_service = JarvisService()

ALLOWED_EXTENSIONS = {'xls', 'xlsx'}


def allowed_file(filename):
    """Проверка допустимого расширения файла"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@jarvis_bp.route('/process', methods=['POST'])
def process_files():
    """Обработка загруженных файлов"""
    try:
        # Проверяем наличие файлов
        if 'files' not in request.files:
            return jsonify({'error': 'Файлы не найдены'}), 400
        
        files = request.files.getlist('files')
        
        if len(files) < 3:
            return jsonify({'error': 'Необходимо загрузить минимум 3 файла'}), 400
        
        # Проверяем наличие всех необходимых типов файлов
        has_prodagi = False
        has_neprol = False
        has_employ = False
        
        valid_files = []
        for file in files:
            if file.filename == '':
                continue
                
            if not allowed_file(file.filename):
                continue
            
            # Используем оригинальное имя для проверки типа
            original_filename = file.filename
            print(f"Обрабатываем файл: {original_filename}")
            
            if original_filename.startswith('Prodagi_VSK'):
                has_prodagi = True
                valid_files.append(file)
            elif original_filename.startswith('не+прол'):
                has_neprol = True
                valid_files.append(file)
            elif original_filename.startswith('employ'):
                has_employ = True
                valid_files.append(file)
            else:
                print(f"Неопознанный файл: {original_filename}")
        
        # Проверяем что все необходимые файлы присутствуют
        if not has_prodagi:
            return jsonify({'error': 'Не найден файл продаж (должен начинаться с "Prodagi_VSK")'}), 400
        
        if not has_neprol:
            return jsonify({'error': 'Не найден файл не пролонгированных (должен начинаться с "не+прол")'}), 400
            
        if not has_employ:
            return jsonify({'error': 'Не найден файл сотрудников (должен начинаться с "employ")'}), 400
        
        print("Все необходимые файлы найдены, запускаем обработку...")
        
        # Запускаем обработку
        success, message = jarvis_service.process_files(valid_files)
        
        if success:
            return jsonify({'message': message})
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        print(f"Ошибка в process_files: {str(e)}")
        return jsonify({'error': str(e)}), 500


@jarvis_bp.route('/status', methods=['GET'])
def get_status():
    """Получение статуса обработки"""
    try:
        status = jarvis_service.get_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@jarvis_bp.route('/cancel', methods=['POST'])
def cancel_processing():
    """Отмена обработки"""
    try:
        result = jarvis_service.cancel_processing()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@jarvis_bp.route('/download', methods=['GET'])
def download_result():
    """Скачивание результата"""
    try:
        result_file = jarvis_service.get_result_file()
        
        if not result_file or not os.path.exists(result_file):
            return jsonify({'error': 'Файл результата не найден'}), 404
        
        return send_file(
            result_file,
            as_attachment=True,
            download_name=Path(result_file).name
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500