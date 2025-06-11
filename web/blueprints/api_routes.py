# web/blueprints/api_routes.py
"""
Blueprint для всех API маршрутов
"""

import os
import configparser
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from core.config.db_config import DATABASES
from core.database.db_utils import check_database_status
from web.services.excel_service import ExcelService
from web.services.correspondences_service import CorrespondencesService
from web.services.data_service import DataService
from web.utils.logging_helper import log_user_access

api_bp = Blueprint('api', __name__)

# Инициализируем сервисы
excel_service = ExcelService()
correspondences_service = CorrespondencesService()
data_service = DataService()


@api_bp.route('/status')
def get_status():
    """Получение статуса баз данных"""
    statuses = {}
    
    for db_name, db_config in DATABASES.items():
        try:
            status = check_database_status(db_config)
            statuses[db_name] = {"status": "connected" if status else "disconnected"}
        except Exception as e:
            statuses[db_name] = {"status": "disconnected", "ERROR": str(e)}

    return jsonify({"databases": statuses})


@api_bp.route('/get_data', methods=['POST'])
def get_data_api():
    """API endpoint для получения данных"""
    try:
        insurance_type = request.form.get('insurance_type')
        channel = request.form.get('channel')
        branch_code = request.form.get('branch_code')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        # Логируем запрос
        log_user_access(
            page="DataVision API",
            client_ip=request.remote_addr,
            current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
            message=f"Запрос данных: {start_date} - {end_date}, тип: {insurance_type}"
        )

        results = data_service.get_kasko_prolongation_data(
            start_date=start_date or datetime.now().strftime('%Y_%m'),
            end_date=end_date or datetime.now().strftime('%Y_%m'),
            insurance_type=insurance_type.split(',') if insurance_type else None,
            channel=channel,
            branch_code=branch_code.split(',') if branch_code else None
        )

        if results:
            return jsonify(results)
        else:
            return jsonify({'error': 'Данные не найдены или произошла ошибка во время запроса'}), 404

    except Exception as e:
        current_app.logger.error(f"Ошибка в get_data_api: {str(e)}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/get-settings', methods=['GET'])
def get_settings():
    """Получение настроек для типа регистрации"""
    register_type = request.args.get('type', 'Ипотека')
    config = configparser.ConfigParser()
    
    try:
        with open('settings_nexus.ini', 'r', encoding='utf-8') as f:
            config.read_file(f)
    except FileNotFoundError:
        return jsonify({"error": "settings_nexus.ini not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if register_type in config:
        return jsonify(dict(config[register_type]))
    else:
        return jsonify({})


@api_bp.route('/save-settings', methods=['POST'])
def save_settings():
    """Сохранение настроек для типа регистрации"""
    try:
        register_type = request.json.get('type')
        settings = request.json.get('settings', {})
        
        config = configparser.ConfigParser()
        
        try:
            with open('settings_nexus.ini', 'r', encoding='utf-8') as f:
                config.read_file(f)
        except FileNotFoundError:
            return jsonify({"error": "settings_nexus.ini not found"}), 404
        
        if not config.has_section(register_type):
            config.add_section(register_type)
            
        for key, value in settings.items():
            config[register_type][key] = value
            
        with open('settings_nexus.ini', 'w', encoding='utf-8') as f:
            config.write(f)
            
        return jsonify({"success": True})
        
    except Exception as e:
        current_app.logger.error(f"Ошибка в save_settings: {str(e)}")
        return jsonify({"error": str(e)}), 500


@api_bp.route('/auto-map-headers', methods=['POST'])
def auto_map_headers():
    """Автоматическое сопоставление заголовков"""
    try:
        data = request.json
        register_type = data.get('registerType', '').lower()
        print (register_type)
        template_headers = data.get('templateHeaders', [])
        file_headers = data.get('fileHeaders', [])

        if not register_type or not template_headers:
            return jsonify({'error': 'Отсутствуют необходимые данные'}), 400

        mappings = correspondences_service.auto_map_headers(
            register_type, template_headers, file_headers
        )

        return jsonify({
            'success': True,
            'mappings': mappings
        })

    except Exception as e:
        current_app.logger.error(f"Ошибка в auto_map_headers: {str(e)}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/save-correspondences', methods=['POST'])
def save_correspondences():
    """Сохранение соответствий заголовков"""
    try:
        data = request.json
        register_type = data.get('registerType', '').lower()
        mappings = data.get('mappings', {})
        
        if not register_type or not mappings:
            return jsonify({'error': 'Отсутствуют необходимые данные'}), 400
        
        success = correspondences_service.save_correspondences(register_type, mappings)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Соответствия успешно сохранены'
            })
        else:
            return jsonify({'error': 'Ошибка при сохранении соответствий'}), 500
        
    except Exception as e:
        current_app.logger.error(f"Ошибка в save_correspondences: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
@api_bp.route('/cancel-processing', methods=['POST'])
def cancel_processing_nexus():
    """
    Отменяет обработку реестра (заглушка для демонстрации).
    """
    # В реальном приложении здесь был бы код для отмены фоновой задачи
    return jsonify({
        'success': True,
        'message': 'Обработка отменена'
    })