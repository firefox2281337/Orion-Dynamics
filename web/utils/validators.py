# web/utils/validators.py
"""
Модуль валидаторов для проверки данных
"""

import re
from datetime import datetime
from core.config.db_config import ALLOWED_EXTENSIONS, DATABASES


class FileValidator:
    """Валидатор для файлов"""
    
    @staticmethod
    def validate_file_extension(filename):
        """
        Проверяет расширение файла
        
        Args:
            filename: Имя файла
            
        Returns:
            bool: True если расширение допустимо
        """
        if not filename or '.' not in filename:
            return False
        
        extension = filename.rsplit('.', 1)[1].lower()
        return extension in ALLOWED_EXTENSIONS
    
    @staticmethod
    def validate_file_size(file, max_size_mb=100):
        """
        Проверяет размер файла
        
        Args:
            file: Объект файла
            max_size_mb: Максимальный размер в МБ
            
        Returns:
            bool: True если размер допустим
        """
        if not file:
            return False
        
        # Получаем размер файла
        file.seek(0, 2)  # Переходим в конец файла
        size = file.tell()
        file.seek(0)  # Возвращаемся в начало
        
        max_size_bytes = max_size_mb * 1024 * 1024
        return size <= max_size_bytes
    
    @staticmethod
    def validate_excel_file(file):
        """
        Комплексная проверка Excel файла
        
        Args:
            file: Объект файла
            
        Returns:
            tuple: (bool, str) - (валиден, сообщение об ошибке)
        """
        if not file:
            return False, "Файл не предоставлен"
        
        if file.filename == '':
            return False, "Имя файла пустое"
        
        if not FileValidator.validate_file_extension(file.filename):
            return False, "Недопустимое расширение файла"
        
        if not FileValidator.validate_file_size(file):
            return False, "Файл слишком большой"
        
        return True, "Файл валиден"


class SQLValidator:
    """Валидатор для SQL запросов"""
    
    # Опасные SQL ключевые слова
    DANGEROUS_KEYWORDS = [
        'DROP', 'DELETE', 'TRUNCATE', 'INSERT', 'UPDATE', 'ALTER',
        'CREATE', 'EXEC', 'EXECUTE', 'sp_', 'xp_'
    ]
    
    @staticmethod
    def validate_database_name(database_name):
        """
        Проверяет имя базы данных
        
        Args:
            database_name: Имя базы данных
            
        Returns:
            bool: True если имя валидно
        """
        return database_name in DATABASES
    
    @staticmethod
    def validate_sql_query(sql_query, allow_modifications=False):
        """
        Проверяет SQL запрос на безопасность
        
        Args:
            sql_query: SQL запрос
            allow_modifications: Разрешить модифицирующие операции
            
        Returns:
            tuple: (bool, str) - (валиден, сообщение об ошибке)
        """
        if not sql_query or not sql_query.strip():
            return False, "SQL запрос пустой"
        
        # Проверяем длину запроса
        if len(sql_query) > 10000:
            return False, "SQL запрос слишком длинный"
        
        # Если не разрешены модификации, проверяем на опасные ключевые слова
        if not allow_modifications:
            sql_upper = sql_query.upper()
            for keyword in SQLValidator.DANGEROUS_KEYWORDS:
                if keyword in sql_upper:
                    return False, f"Обнаружено опасное ключевое слово: {keyword}"
        
        # Проверяем на SQL инъекции
        if SQLValidator._check_sql_injection(sql_query):
            return False, "Обнаружена потенциальная SQL инъекция"
        
        return True, "SQL запрос валиден"
    
    @staticmethod
    def _check_sql_injection(sql_query):
        """
        Проверяет на потенциальные SQL инъекции
        
        Args:
            sql_query: SQL запрос
            
        Returns:
            bool: True если обнаружена потенциальная инъекция
        """
        # Простые паттерны SQL инъекций
        injection_patterns = [
            r"'\s*;\s*",  # '; 
            r"--",        # Комментарии
            r"/\*.*\*/",  # Многострочные комментарии
            r"union\s+select",  # UNION SELECT
            r"exec\s*\(",  # EXEC(
            r"sp_\w+",    # Системные процедуры
        ]
        
        sql_lower = sql_query.lower()
        for pattern in injection_patterns:
            if re.search(pattern, sql_lower, re.IGNORECASE):
                return True
        
        return False


class DataValidator:
    """Валидатор для данных"""
    
    @staticmethod
    def validate_date_format(date_string, format_string='%Y-%m-%d'):
        """
        Проверяет формат даты
        
        Args:
            date_string: Строка с датой
            format_string: Формат даты
            
        Returns:
            tuple: (bool, datetime|None) - (валидна, объект даты)
        """
        try:
            date_obj = datetime.strptime(date_string, format_string)
            return True, date_obj
        except (ValueError, TypeError):
            return False, None
    
    @staticmethod
    def validate_email(email):
        """
        Проверяет формат email
        
        Args:
            email: Email адрес
            
        Returns:
            bool: True если email валиден
        """
        if not email:
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_phone(phone):
        """
        Проверяет формат телефона
        
        Args:
            phone: Номер телефона
            
        Returns:
            bool: True если телефон валиден
        """
        if not phone:
            return False
        
        # Убираем все не-цифровые символы
        phone_digits = re.sub(r'\D', '', phone)
        
        # Проверяем длину (от 10 до 15 цифр)
        return 10 <= len(phone_digits) <= 15
    
    @staticmethod
    def validate_required_fields(data, required_fields):
        """
        Проверяет наличие обязательных полей
        
        Args:
            data: Словарь с данными
            required_fields: Список обязательных полей
            
        Returns:
            tuple: (bool, list) - (валидны, список отсутствующих полей)
        """
        if not isinstance(data, dict):
            return False, required_fields
        
        missing_fields = []
        for field in required_fields:
            if field not in data or not data[field]:
                missing_fields.append(field)
        
        return len(missing_fields) == 0, missing_fields
    
    @staticmethod
    def validate_numeric_range(value, min_value=None, max_value=None):
        """
        Проверяет числовое значение в диапазоне
        
        Args:
            value: Значение для проверки
            min_value: Минимальное значение
            max_value: Максимальное значение
            
        Returns:
            tuple: (bool, str) - (валидно, сообщение об ошибке)
        """
        try:
            num_value = float(value)
        except (ValueError, TypeError):
            return False, "Значение не является числом"
        
        if min_value is not None and num_value < min_value:
            return False, f"Значение меньше минимального ({min_value})"
        
        if max_value is not None and num_value > max_value:
            return False, f"Значение больше максимального ({max_value})"
        
        return True, "Значение валидно"


class FormValidator:
    """Валидатор для форм"""
    
    @staticmethod
    def validate_processing_form(form_data):
        """
        Проверяет форму обработки файлов
        
        Args:
            form_data: Данные формы
            
        Returns:
            tuple: (bool, list) - (валидна, список ошибок)
        """
        errors = []
        
        # Проверяем наличие файлов
        if 'files' not in form_data or not form_data['files']:
            errors.append("Файлы не загружены")
        
        # Проверяем типы файлов
        required_file_types = ['Речевая', 'call']
        found_types = []
        
        if 'files' in form_data:
            for file in form_data['files']:
                for file_type in required_file_types:
                    if file.filename.startswith(file_type):
                        found_types.append(file_type)
                        break
        
        missing_types = set(required_file_types) - set(found_types)
        if missing_types:
            errors.append(f"Отсутствуют файлы типов: {', '.join(missing_types)}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_settings_form(form_data):
        """
        Проверяет форму настроек
        
        Args:
            form_data: Данные формы
            
        Returns:
            tuple: (bool, list) - (валидна, список ошибок)
        """
        errors = []
        
        required_fields = ['type', 'settings']
        is_valid, missing_fields = DataValidator.validate_required_fields(
            form_data, required_fields
        )
        
        if not is_valid:
            errors.append(f"Отсутствуют обязательные поля: {', '.join(missing_fields)}")
        
        # Проверяем настройки
        if 'settings' in form_data and not isinstance(form_data['settings'], dict):
            errors.append("Настройки должны быть в формате словаря")
        
        return len(errors) == 0, errors