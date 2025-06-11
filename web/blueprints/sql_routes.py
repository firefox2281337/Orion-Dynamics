# web/blueprints/sql_routes.py
"""
Blueprint для SQL операций
"""

from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, send_file
from core.config.db_config import DATABASES
from web.services.sql_service import SQLService
from web.services.excel_service import ExcelService
from web.utils.access_control import require_ip_access
from web.utils.logging_helper import log_user_access, log_query_info

sql_bp = Blueprint('sql', __name__)
sql_service = SQLService()
excel_service = ExcelService()


@sql_bp.route('/queries')
@require_ip_access
def sql_queries():
    """Страница для выполнения SQL-запросов"""
    last_check = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    
    log_user_access(
        page="site/sql_queries.html",
        client_ip=request.remote_addr,
        current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
        message="Пользователь зашёл на sql_queries.html"
    )
    
    return render_template(
        'site/sql_queries.html',
        DATABASES=DATABASES,
        last_check=last_check
    )


@sql_bp.route('/execute', methods=['POST'])
@require_ip_access
def execute_sql_route():
    """API endpoint для выполнения SQL запроса"""
    try:
        data = request.get_json()
        sql_query = data.get('sql_query')
        database = data.get('database')
        
        if not sql_query or not database:
            return jsonify({'error': 'Требуется SQL-запрос и выбранная база данных'}), 400
        
        # Логируем запрос
        log_query_info(
            client_ip=request.remote_addr,
            current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
            data=data,
            sql_query=sql_query,
            database=database
        )
        
        results = sql_service.execute_sql(sql_query, database)
        return jsonify(results)
        
    except Exception as e:
        log_query_info(
            client_ip=request.remote_addr,
            current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
            data=request.get_json(),
            error=str(e)
        )
        return jsonify({'error': f'Ошибка обработки запроса: {str(e)}'}), 500


@sql_bp.route('/save_excel', methods=['POST'])
@require_ip_access
def save_excel():
    """API endpoint для сохранения данных в Excel файл"""
    try:
        data = request.get_json()
        table_data = data.get('table_data')
        
        if not table_data or len(table_data) < 2:
            return jsonify({'error': 'Данные таблицы не предоставлены или неверный формат'}), 400
        
        mem = excel_service.save_to_excel(table_data)
        
        return send_file(
            mem,
            as_attachment=True,
            download_name='results.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        return jsonify({'error': f'Ошибка сохранения Excel: {str(e)}'}), 500


@sql_bp.route('/query', methods=['POST'])
def query():
    """API endpoint для выполнения SQL запроса (внешний API)"""
    try:
        data = request.json
        sql_query = data.get('query')
        database = data.get('database')
        
        if not sql_query or not database:
            return jsonify({"error": "SQL-запрос или база данных не предоставлены"}), 400
        
        # Логируем запрос
        log_query_info(
            client_ip=request.remote_addr,
            current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
            data=data,
            sql_query=sql_query,
            database=database
        )
        
        result = sql_service.execute_query_api(sql_query, database)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": f"Ошибка выполнения запроса: {str(e)}"}), 500