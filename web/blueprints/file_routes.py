# web/blueprints/file_routes.py
"""
Blueprint для работы с файлами
"""

from datetime import datetime
from collections import defaultdict
from flask import Blueprint, render_template, request, send_file, send_from_directory, jsonify, abort
from core.config.db_config import ALLOWED_IPS
from web.services.file_service import FileService
from web.utils.logging_helper import log_user_access
from web.utils.access_control import require_ip_access

file_bp = Blueprint('files', __name__)
file_service = FileService()


@file_bp.route('/software', methods=['GET', 'POST'])
@require_ip_access
def software_page():
    """Страница загрузки программного обеспечения"""
    last_check = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    current_year = datetime.now().year
    
    files = file_service.load_files()
    grouped_files = defaultdict(list)
    for file in files:
        grouped_files[file['category']].append(file)
    
    grouped_files = dict(grouped_files)
    
    log_user_access(
        page="site/software.html",
        client_ip=request.remote_addr,
        current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
        message="Пользователь зашёл на software.html"
    )
    
    return render_template(
        'site/software_download.html',
        current_year=current_year,
        last_check=last_check,
        grouped_files=grouped_files
    )


@file_bp.route('/download/<file_id>')
def download_file(file_id):
    """Скачивание файла по ID"""
    file_info = file_service.get_file_by_id(file_id)
    if file_info:
        return send_from_directory(
            file_service.files_dir,
            file_info['filename'],
            as_attachment=True
        )
    abort(404)


@file_bp.route('/preview/<file_id>')
def preview_file(file_id):
    """Превью файла"""
    preview_data = file_service.create_preview(file_id)
    if preview_data:
        return jsonify(preview_data)
    abort(404)


@file_bp.route('/raw/<file_id>')
def raw_file(file_id):
    """Возвращает сырой файл для просмотра в браузере"""
    file_info = file_service.get_file_by_id(file_id)
    if not file_info:
        abort(404)
    
    file_path = file_service.get_file_path(file_info['filename'])
    return send_file(file_path)