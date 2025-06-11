# web/routes/lost_contracts_routes.py
"""
Маршруты для обработки потерянных договоров
"""

from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
from pathlib import Path
import os

from web.services.lost_contracts_service import LostContractsService

# Создаем blueprint
lost_contracts_bp = Blueprint('lost_contracts', __name__, url_prefix='/lost_contracts')

# Инициализируем сервис
lost_contracts_service = LostContractsService()

ALLOWED_EXTENSIONS = {'xls', 'xlsx'}


def allowed_file(filename):
    """Проверка допустимого расширения файла"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@lost_contracts_bp.route('/process', methods=['POST'])
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
        if not file.filename.startswith('Договора+по'):
            return jsonify({'error': 'Файл должен начинаться с "Договора+по"'}), 400
        
        print(f"Обрабатываем файл: {file.filename}")
        
        # Запускаем обработку
        success, message = lost_contracts_service.process_file(file)
        
        if success:
            return jsonify({'message': message})
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        print(f"Ошибка в process_file: {str(e)}")
        return jsonify({'error': str(e)}), 500


@lost_contracts_bp.route('/status', methods=['GET'])
def get_status():
    """Получение статуса обработки"""
    try:
        status = lost_contracts_service.get_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@lost_contracts_bp.route('/cancel', methods=['POST'])
def cancel_processing():
    """Отмена обработки"""
    try:
        result = lost_contracts_service.cancel_processing()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@lost_contracts_bp.route('/download', methods=['GET'])
def download_result():
    """Скачивание результата"""
    try:
        result_file = lost_contracts_service.get_result_file()
        
        if not result_file or not os.path.exists(result_file):
            return jsonify({'error': 'Файл результата не найден'}), 404
        
        return send_file(
            result_file,
            as_attachment=True,
            download_name=Path(result_file).name
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500