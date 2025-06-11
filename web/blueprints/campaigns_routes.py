# web/routes/campaigns_routes.py
"""
Маршруты для проверки кампаний
"""

from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
from pathlib import Path
import os

from web.services.campaigns_service import CampaignsService

# Создаем blueprint
campaigns_bp = Blueprint('campaigns', __name__, url_prefix='/campaigns')

# Инициализируем сервис
campaigns_service = CampaignsService()

ALLOWED_EXTENSIONS = {'xls', 'xlsx'}


def allowed_file(filename):
    """Проверка допустимого расширения файла"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@campaigns_bp.route('/process', methods=['POST'])
def process_file():
    """Обработка загруженного файла"""
    try:
        # Проверяем наличие файла
        if 'file' not in request.files:
            return jsonify({'error': 'Файл не найден'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
            
        if not allowed_file(file.filename):
            return jsonify({'error': 'Недопустимый тип файла'}), 400
        
        # Проверяем что файл начинается с нужного префикса
        if not file.filename.startswith('cgr'):
            return jsonify({'error': 'Файл должен начинаться с "cgr"'}), 400
        
        print(f"Обрабатываем файл: {file.filename}")
        
        # Запускаем обработку
        success, message = campaigns_service.process_file(file)
        
        if success:
            return jsonify({'message': message})
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        print(f"Ошибка в process_file: {str(e)}")
        return jsonify({'error': str(e)}), 500


@campaigns_bp.route('/status', methods=['GET'])
def get_status():
    """Получение статуса обработки"""
    try:
        status = campaigns_service.get_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@campaigns_bp.route('/cancel', methods=['POST'])
def cancel_processing():
    """Отмена обработки"""
    try:
        result = campaigns_service.cancel_processing()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@campaigns_bp.route('/download', methods=['GET'])
def download_result():
    """Скачивание результата"""
    try:
        result_file = campaigns_service.get_result_file()
        
        if not result_file or not os.path.exists(result_file):
            return jsonify({'error': 'Файл результата не найден'}), 404
        
        return send_file(
            result_file,
            as_attachment=True,
            download_name=Path(result_file).name
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500