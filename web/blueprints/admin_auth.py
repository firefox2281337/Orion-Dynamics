# web/blueprints/admin_auth.py
"""
Аутентификация и авторизация для админ панели
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from web.utils.admin_security import admin_security, security_check
import logging

auth_bp = Blueprint('admin_auth', __name__, url_prefix='/admin')
logger = logging.getLogger(__name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
@security_check
def admin_login():
    """Страница входа в админ панель"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        client_ip = admin_security.get_client_ip()
        
        # Проверяем учетные данные
        if admin_security.verify_password(username, password):
            # Успешный вход
            admin_security.record_login_attempt(client_ip, success=True, username=username)
            admin_security.create_session(username, client_ip)
            
            flash('Успешный вход в систему', 'success')
            return redirect(url_for('admin.admin_dashboard'))
        else:
            # Неудачная попытка
            admin_security.record_login_attempt(client_ip, success=False, username=username)
            flash('Неверные учетные данные', 'error')
    
    return render_template('admin/login.html')

@auth_bp.route('/logout')
def admin_logout():
    """Выход из админ панели"""
    admin_security.destroy_session()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('admin_auth.admin_login'))

@auth_bp.route('/security-status')
@security_check
def security_status():
    """API для получения статуса безопасности"""
    return {
        'active_sessions': len(admin_security.active_sessions),
        'blocked_ips': len(admin_security.blocked_ips),
        'recent_events': admin_security.security_events[-10:],
        'security_level': 'high' if len(admin_security.blocked_ips) == 0 else 'medium'
    }