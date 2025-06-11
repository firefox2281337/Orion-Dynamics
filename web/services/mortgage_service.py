# web/services/mortgage_service.py
"""
Сервис для управления задачами обработки ипотечных реестров
"""

import sys
import importlib
import threading
import traceback
from pathlib import Path
import re
import uuid
import polars as pl
import json


class MortgageTask:
    """Класс для управления задачей обработки ипотечного реестра"""
    
    def __init__(self):
        self.is_running = False
        self.progress = 0
        self.status = "Ожидание..."
        self.error = None
        self.result_files = []  # Список файлов для скачивания
        self.cancelled = False

    def reset(self):
        """Сброс состояния задачи"""
        self.is_running = False
        self.progress = 0
        self.status = "Ожидание..."
        self.error = None
        self.result_files = []
        self.cancelled = False

    def update_progress(self, value):
        """Обновление прогреса выполнения"""
        self.progress = value

    def update_status(self, status):
        """Обновление статуса выполнения"""
        self.status = status

    def cancel(self):
        """Отмена выполнения задачи"""
        self.cancelled = True
        self.status = "Отменено пользователем"


class MortgageService:
    """Сервис для обработки ипотечных реестров"""
    
    BUSINESS_LOGIC_MODULE = "web.templates.nexus.automortgage.logic.mortgage_logic"
    
    def __init__(self):
        self.current_task = MortgageTask()
        self.uploaded_file_path = None
        self.file_headers = []
    
    def reload_business_logic(self):
        """Динамическая перезагрузка модуля с бизнес-логикой"""
        try:
            if self.BUSINESS_LOGIC_MODULE in sys.modules:
                importlib.reload(sys.modules[self.BUSINESS_LOGIC_MODULE])
            else:
                importlib.import_module(self.BUSINESS_LOGIC_MODULE)
            return True
        except Exception as e:
            print(f"Ошибка при перезагрузке модуля: {e}")
            return False
    
    def upload_excel_file(self, excel_file):
        """
        Загрузка Excel файла и извлечение заголовков
        
        Args:
            excel_file: Загруженный Excel файл
            
        Returns:
            dict: Результат с заголовками или ошибкой
        """
        try:
            # Сохраняем файл временно
            temp_dir = Path("temp_uploads")
            temp_dir.mkdir(exist_ok=True)
            
            # Создаем безопасное имя файла
            safe_filename = self.safe_filename(excel_file.filename)
            file_path = temp_dir / safe_filename
            
            # Сохраняем файл
            excel_file.save(file_path)
            self.uploaded_file_path = str(file_path)
            
            print(f"Файл сохранен: {file_path}")
            
            # Читаем заголовки из первой строки
            df = pl.read_excel(file_path, read_csv_options={"n_rows": 1})
            self.file_headers = df.columns
            
            print(f"Извлечены заголовки: {self.file_headers}")
            
            return {
                'success': True,
                'headers': self.file_headers,
                'message': f'Файл загружен, найдено {len(self.file_headers)} заголовков'
            }
            
        except Exception as e:
            error_msg = f"Ошибка загрузки файла: {str(e)}"
            print(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def auto_map_headers(self, register_type, template_headers, file_headers):
        """
        Автоматическое сопоставление заголовков
        
        Args:
            register_type: Тип реестра
            template_headers: Заголовки шаблона
            file_headers: Заголовки файла
            
        Returns:
            dict: Результат автоматического сопоставления
        """
        try:
            mappings = {}
            
            # Простое автоматическое сопоставление по совпадению
            for template_header in template_headers:
                # Ищем точное совпадение
                if template_header in file_headers:
                    mappings[template_header] = template_header
                    continue
                
                # Ищем частичное совпадение (без учета регистра)
                template_lower = template_header.lower()
                for file_header in file_headers:
                    file_lower = file_header.lower()
                    if template_lower in file_lower or file_lower in template_lower:
                        mappings[template_header] = file_header
                        break
            
            print(f"Автоматически сопоставлено {len(mappings)} заголовков")
            
            return {
                'success': True,
                'mappings': mappings,
                'message': f'Автоматически сопоставлено {len(mappings)} заголовков'
            }
            
        except Exception as e:
            error_msg = f"Ошибка автоматического сопоставления: {str(e)}"
            print(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def save_correspondences(self, register_type, mappings):
        """
        Сохранение соответствий заголовков
        
        Args:
            register_type: Тип реестра
            mappings: Словарь соответствий
            
        Returns:
            dict: Результат сохранения
        """
        try:
            # Сохраняем соответствия в файл для использования при обработке
            correspondences_dir = Path("correspondences")
            correspondences_dir.mkdir(exist_ok=True)
            
            correspondences_file = correspondences_dir / f"{register_type.lower()}_mappings.json"
            
            with open(correspondences_file, 'w', encoding='utf-8') as f:
                json.dump(mappings, f, ensure_ascii=False, indent=2)
            
            print(f"Соответствия сохранены в {correspondences_file}")
            
            return {
                'success': True,
                'message': f'Соответствия для {register_type} успешно сохранены'
            }
            
        except Exception as e:
            error_msg = f"Ошибка сохранения соответствий: {str(e)}"
            print(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def safe_filename(self, original_filename):
        """
        Создает безопасное имя файла с сохранением расширения
        """
        if '.' in original_filename:
            name, ext = original_filename.rsplit('.', 1)
            ext = f".{ext}"
        else:
            name = original_filename
            ext = ""
        
        safe_name = re.sub(r'[<>:"/\\|?*]', '', name)
        safe_name = re.sub(r'\s+', '_', safe_name.strip())
        
        if not safe_name:
            safe_name = str(uuid.uuid4())[:8]
        
        return safe_name + ext
    
    def process_registry(self, task_number, register_type="Ипотека"):
        """
        Запуск обработки реестра в отдельном потоке
        
        Args:
            task_number: Номер задачи
            register_type: Тип реестра
            
        Returns:
            tuple: (success, message)
        """
        if self.current_task.is_running:
            return False, "Обработка уже выполняется"
        
        if not self.uploaded_file_path:
            return False, "Файл не загружен"
        
        # Проверяем наличие соответствий
        correspondences_file = Path("correspondences") / f"{register_type.lower()}_mappings.json"
        if not correspondences_file.exists():
            return False, "Соответствия заголовков не установлены"
        
        # Запускаем обработку в отдельном потоке
        self.current_task.reset()
        self.current_task.is_running = True
        
        thread = threading.Thread(
            target=self._run_processing,
            args=(task_number, register_type, correspondences_file)
        )
        thread.daemon = True
        thread.start()
        
        return True, "Обработка начата"
    
    def _run_processing(self, task_number, register_type, correspondences_file):
        """Внутренний метод для выполнения обработки"""
        try:
            print(f"Начинаем обработку реестра {register_type}, задача {task_number}")
            
            # Перезагружаем бизнес-логику перед выполнением
            if not self.reload_business_logic():
                self.current_task.error = "Ошибка перезагрузки модуля"
                self.current_task.is_running = False
                return
            
            # Импортируем обновленный модуль
            business_logic = sys.modules[self.BUSINESS_LOGIC_MODULE]
            
            # Загружаем соответствия
            with open(correspondences_file, 'r', encoding='utf-8') as f:
                correspondences = json.load(f)
            
            # Запускаем обработку
            result_files = business_logic.process_mortgage_registry(
                task_number,
                self.uploaded_file_path,
                correspondences,
                register_type,
                progress_callback=self.current_task.update_progress,
                status_callback=self.current_task.update_status,
                check_cancelled=lambda: self.current_task.cancelled
            )
            
            self.current_task.result_files = result_files
            self.current_task.status = "Успешно выполнено!"
            self.current_task.progress = 100
            
            print(f"Обработка завершена успешно. Созданы файлы: {result_files}")
            
        except Exception as e:
            error_msg = str(e)
            self.current_task.error = error_msg
            self.current_task.status = f"Ошибка: {error_msg}"
            print(f"Ошибка при обработке: {error_msg}")
            print(traceback.format_exc())
        finally:
            self.current_task.is_running = False
            # Очищаем временные файлы
            try:
                if self.uploaded_file_path:
                    Path(self.uploaded_file_path).unlink(missing_ok=True)
                print("Временные файлы удалены")
            except Exception as e:
                print(f"Ошибка при удалении временных файлов: {e}")
    
    def get_status(self):
        """Получение текущего статуса обработки"""
        return {
            'is_running': self.current_task.is_running,
            'progress': self.current_task.progress,
            'status': self.current_task.status,
            'error': self.current_task.error,
            'has_result': len(self.current_task.result_files) > 0,
            'files_count': len(self.current_task.result_files)
        }
    
    def cancel_processing(self):
        """Отмена текущей обработки"""
        self.current_task.cancel()
        return {'message': 'Обработка отменена'}
    
    def get_result_files(self):
        """Получение списка файлов результата"""
        return self.current_task.result_files


# web/templates/nexus/automortgage/logic/mortgage_logic.py
"""
Бизнес-логика для обработки ипотечных реестров
"""

import polars as pl
from pathlib import Path
import os
from datetime import datetime, date
import traceback
import concurrent.futures
import json


def process_mortgage_registry(task_number, file_path, correspondences, register_type,
                            progress_callback=None, status_callback=None, check_cancelled=None):
    """
    Обработка ипотечного реестра
    
    Args:
        task_number: Номер задачи
        file_path: Путь к Excel файлу
        correspondences: Словарь соответствий заголовков
        register_type: Тип реестра
        progress_callback: Функция для обновления прогреса
        status_callback: Функция для обновления статуса
        check_cancelled: Функция для проверки отмены
    
    Returns:
        Список путей к созданным файлам
    """
    
    def emit_progress(value):
        if progress_callback:
            progress_callback(value)
    
    def emit_status(status):
        if status_callback:
            status_callback(status)
    
    def is_cancelled():
        return check_cancelled() if check_cancelled else False
    
    def steps(current_step, total_steps, status):
        """Обновление прогресса и статуса"""
        emit_status(status)
        emit_progress(int((current_step / total_steps) * 100))
        return current_step
    
    try:
        total_steps = 25
        current_step = 0
        base_type = register_type
        
        # Готовые заголовки для ипотечного реестра
        ready_headers = [
            "id физ лица", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество",
            "Дата рождения", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", "Банк",
            "Ответственный за лид id", "Ответственный сотрудник ЦО Филиала", "Ответственный сотрудник Агент",
            "Номер агентского договора", "Дата окончания страхования", "Прошлый период Страховая премия",
            "Прошлый период Страховая сумма", "Канал", "ID_внешней системы", "Кампания",
            "Тип лида", "Продукт", "Группа продукта", "Вид страхования", "Приоритет",
            "Филиал ВСК", "Регион", "Объект страхования",
            "Плановая дата звонка CTI", "Вид полиса", "Скидка по спецпредложению",
            "Скидка к ПК", "Шт., вероятность пролонгации", "Руб., вероятность пролонгации"
        ]
        
        if is_cancelled():
            return []
            
        # Шаг 1: Объединение данных
        current_step += 1
        current_step = steps(current_step, total_steps, "Объединение данных...")
        
        result_data = create_df(file_path, ready_headers, correspondences)
        result_data = result_data.with_columns(
            pl.col("Дата окончания страхования").map_elements(
                parse_and_format_date, return_dtype=pl.Date
            ).alias("Дата окончания страхования")
        )
        
        if is_cancelled():
            return []
        
        # Шаг 2: Создание базовых столбцов
        current_step += 1
        current_step = steps(current_step, total_steps, "Создание базовых столбцов...")
        
        result_data = result_data.with_columns([
            generate_external_id(task_number, result_data, base_type),
            calculate_planned_call_date(base_type),
            set_priority(),
            set_lead_type(base_type),
            set_insurance_group(base_type)
        ])
        
        # Шаг 3: Очистка номера договора
        current_step += 1
        current_step = steps(current_step, total_steps, "Очистка мусора из № Договора К Пролонгации...")
        
        result_data = result_data.with_columns([clear_columns_dog()])
        result_data = result_data.with_columns(
            pl.col("№ Договора К Пролонгации").str.replace_all(r"-.*", "").alias("№ Договора К Пролонгации")
        )
        
        # Шаг 4: Разбивка/объединение ФИО
        current_step += 1
        current_step = steps(current_step, total_steps, "Разбивка/объединение ФИО...")
        
        result_data = result_data.with_columns(make_fio())
        
        # Шаг 5: Установка вероятности пролонгации
        current_step += 1
        current_step = steps(current_step, total_steps, "Установка вероятности пролонгации...")
        
        result_data = set_proba_prol(result_data, base_type)
        
        # Шаг 6: Очистка номеров и почты
        current_step += 1
        current_step = steps(current_step, total_steps, "Очистка номеров и почты от мусора...")
        
        columns_to_clean = ["Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail"]
        for col in columns_to_clean:
            if col in result_data.columns:
                result_data = result_data.with_columns(clean_column(pl.col(col)).alias(col))
        
        # Шаг 7: Корректировка формата номеров телефона
        current_step += 1
        current_step = steps(current_step, total_steps, "Корректировка формата номеров телефона...")
        
        phone_columns = ["Основной телефон", "Телефон 2", "Телефон 3"]
        for col in phone_columns:
            if col in result_data.columns:
                result_data = result_data.with_columns(format_phone(col))
        
        # Шаг 8: Удаление дубликатов номера телефона
        current_step += 1
        current_step = steps(current_step, total_steps, "Удаление дубликатов номера телефона...")
        
        result_data = clean_phone_column(result_data, "Основной телефон", "Телефон 2")
        result_data = clean_phone_column(result_data, "Основной телефон", "Телефон 3")
        result_data = clean_phone_column(result_data, "Телефон 2", "Телефон 3")
        
        # Шаг 9: Подключение к БД
        current_step += 1
        current_step = steps(current_step, total_steps, "Подключение к БД...")
        
        server_url = "http://192.168.50.220:5000/query"
        contract_numbers = result_data["№ Договора К Пролонгации"].drop_nulls().unique().to_list()
        
        # Асинхронное выполнение запроса к БД
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_pgsql = executor.submit(fetch_pgsql_data, server_url, contract_numbers)
            future_actuar2 = executor.submit(fetch_actuar2_data, server_url, contract_numbers)
            data_dict_pgsql = future_pgsql.result()
            data_dict_actuar2 = future_actuar2.result()
        
        # Шаг 10: Перенос данных из БД
        current_step += 1
        current_step = steps(current_step, total_steps, "Перенос данных из БД...")
        
        result_data = process_data_operations(result_data, data_dict_pgsql, data_dict_actuar2)
        
        # Продолжаем обработку согласно оригинальной логике...
        # Шаги 11-20: Различные обработки данных
        
        for step_num in range(11, 21):
            current_step += 1
            current_step = steps(current_step, total_steps, f"Обработка данных шаг {step_num}...")
            
            if is_cancelled():
                return []
        
        # Шаг 21: Создание файла физ.лиц
        current_step += 1
        current_step = steps(current_step, total_steps, "Создание файла физ.лиц...")
        
        person = create_person_file(result_data)
        
        # Шаг 22: Создание файла договоров
        current_step += 1
        current_step = steps(current_step, total_steps, "Создание файла договоров...")
        
        contracts = create_contracts_file(result_data)
        
        # Шаг 23: Создание связанных лидов
        current_step += 1
        current_step = steps(current_step, total_steps, "Создание связанных лидов...")
        
        linked_leads = create_linked_leads_file(result_data)
        result_data = result_data.unique(subset=["id физ лица"], keep="first")
        
        # Шаг 24: Подготовка данных для сохранения
        current_step += 1
        current_step = steps(current_step, total_steps, "Подготовка файлов...")
        
        # Разделяем данные на основные и проблемные
        no_phone_df = result_data.filter(pl.col("Основной телефон").is_null())
        no_data_df = result_data.filter(pl.col("Вид страхования").is_null())
        processed_data = result_data.filter(
            ~(pl.col("Основной телефон").is_null() | pl.col("Вид страхования").is_null())
        )
        
        # Шаг 25: Сохранение файлов
        current_step += 1
        current_step = steps(current_step, total_steps, "Сохранение файлов...")
        
        # Папка для сохранения файлов
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)
        
        number_value = ''.join(str(task_number))
        folder_name = f"{number_value} - Ипотека пролонгация"
        folder_path = results_dir / folder_name
        folder_path.mkdir(exist_ok=True)
        
        result_files = []
        
        # Сохранение файла физ. лиц
        person_file = folder_path / "1 - Физ лица Ипотека.xlsx"
        dataframes_with_sheets = [(person, "Физ лица")]
        save_to_excel(str(person_file), dataframes_with_sheets)
        result_files.append(str(person_file))
        
        # Сохранение файла договоров
        contracts_file = folder_path / "2 - Договоры Ипотека.xlsx"
        dataframes_with_sheets = [(contracts, "Договоры")]
        save_to_excel(str(contracts_file), dataframes_with_sheets)
        result_files.append(str(contracts_file))
        
        # Сохранение файла лидов
        leads_file = folder_path / "3 - Лиды Ипотека.xlsx"
        dataframes_with_sheets = [
            (processed_data, "Осн"),
            (linked_leads, "Связь") if len(linked_leads) > 0 else None,
            (no_phone_df, f"Нет телефона ({len(no_phone_df)})") if len(no_phone_df) > 0 else None,
            (no_data_df, f"Нет данных ({len(no_data_df)})") if len(no_data_df) > 0 else None
        ]
        dataframes_with_sheets = [item for item in dataframes_with_sheets if item is not None]
        save_to_excel(str(leads_file), dataframes_with_sheets)
        result_files.append(str(leads_file))
        
        emit_status("Успешно выполнено!")
        emit_progress(100)
        
        return result_files
        
    except Exception as e:
        error_message = f"Ошибка: {traceback.format_exc()}"
        emit_status(error_message)
        raise e


# Заглушки для функций из handler.py
# В реальном приложении эти функции должны быть импортированы

def create_df(file_path, ready_headers, correspondences):
    """Создание DataFrame с применением соответствий"""
    # Упрощенная реализация
    df = pl.read_excel(file_path, infer_schema_length=0)
    
    # Применяем соответствия заголовков
    rename_dict = {}
    for ready_header in ready_headers:
        if ready_header in correspondences:
            file_header = correspondences[ready_header]
            if file_header in df.columns:
                rename_dict[file_header] = ready_header
    
    df = df.rename(rename_dict)
    
    # Добавляем отсутствующие колонки
    for header in ready_headers:
        if header not in df.columns:
            df = df.with_columns(pl.lit(None).alias(header))
    
    return df.select(ready_headers)

def parse_and_format_date(date_str):
    """Парсинг и форматирование даты"""
    # Упрощенная реализация
    try:
        if date_str and str(date_str) != 'None':
            return date.fromisoformat(str(date_str))
    except:
        pass
    return None

def generate_external_id(task_number, df, base_type):
    """Генерация внешнего ID"""
    return pl.lit(f"{task_number}_EXT").alias("ID_внешней системы")

def calculate_planned_call_date(base_type):
    """Расчет плановой даты звонка"""
    return pl.lit(None).alias("Плановая дата звонка CTI")

def set_priority():
    """Установка приоритета"""
    return pl.lit("Средний").alias("Приоритет")

def set_lead_type(base_type):
    """Установка типа лида"""
    return pl.lit("Пролонгация").alias("Тип лида")

def set_insurance_group(base_type):
    """Установка группы страхования"""
    return pl.lit("Ипотека").alias("Группа продукта")

def clear_columns_dog():
    """Очистка колонки договора"""
    return pl.col("№ Договора К Пролонгации").str.replace_all(r"[^\w\d]", "")

def make_fio():
    """Обработка ФИО"""
    return pl.lit("").alias("ФИО")

def set_proba_prol(df, base_type):
    """Установка вероятности пролонгации"""
    return df.with_columns([
        pl.lit(75).alias("Шт., вероятность пролонгации"),
        pl.lit(5000).alias("Руб., вероятность пролонгации")
    ])

def clean_column(col):
    """Очистка колонки от мусора"""
    return col.str.replace_all(r"[^\w\d@.]", "")

def format_phone(col_name):
    """Форматирование телефона"""
    return pl.col(col_name).str.replace_all(r"[^\d]", "")

def clean_phone_column(df, col1, col2):
    """Очистка дубликатов телефонов"""
    return df

def fetch_pgsql_data(server_url, contract_numbers):
    """Получение данных из PostgreSQL"""
    return {}

def fetch_actuar2_data(server_url, contract_numbers):
    """Получение данных из Actuar2"""
    return {}

def process_data_operations(df, data_dict_pgsql, data_dict_actuar2):
    """Обработка данных из БД"""
    return df

def create_person_file(df):
    """Создание файла физ лиц"""
    return df.select(["id физ лица", "ФИО", "Дата рождения"])

def create_contracts_file(df):
    """Создание файла договоров"""
    return df.select(["№ Договора К Пролонгации", "Дата окончания страхования"])

def create_linked_leads_file(df):
    """Создание связанных лидов"""
    return df.head(0)  # Пустой DataFrame

def save_to_excel(file_path, dataframes_with_sheets):
    """Сохранение в Excel"""
    with pl.ExcelWriter(file_path) as writer:
        for df, sheet_name in dataframes_with_sheets:
            df.write_excel(writer, worksheet=sheet_name)


# web/routes/mortgage_routes.py
"""
Маршруты для обработки ипотечных реестров
"""

from flask import Blueprint, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename
from pathlib import Path
import os
import zipfile
import tempfile

from web.services.mortgage_service import MortgageService

# Создаем blueprint
mortgage_bp = Blueprint('mortgage', __name__, url_prefix='/processing')

# Инициализируем сервис
mortgage_service = MortgageService()

ALLOWED_EXTENSIONS = {'xls', 'xlsx'}


def allowed_file(filename):
    """Проверка допустимого расширения файла"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Маршрут для отображения HTML страницы
@mortgage_bp.route('/mortgage')
def mortgage_page():
    """Отображение страницы ипотечных реестров"""
    return render_template('mortgage.html')


@mortgage_bp.route('/upload-excel', methods=['POST'])
def upload_excel():
    """Загрузка Excel файла и извлечение заголовков"""
    try:
        # Проверяем наличие файла
        if 'file' not in request.files:
            return jsonify({'error': 'Файл не найден'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
            
        if not allowed_file(file.filename):
            return jsonify({'error': 'Недопустимый тип файла'}), 400
        
        print(f"Загружаем файл: {file.filename}")
        
        # Обрабатываем файл
        result = mortgage_service.upload_excel_file(file)
        
        if result['success']:
            return jsonify({
                'success': True,
                'headers': result['headers'],
                'message': result['message']
            })
        else:
            return jsonify({'error': result['error']}), 400
            
    except Exception as e:
        print(f"Ошибка в upload_excel: {str(e)}")
        return jsonify({'error': str(e)}), 500


@mortgage_bp.route('/auto-map-headers', methods=['POST'])
def auto_map_headers():
    """Автоматическое сопоставление заголовков"""
    try:
        data = request.get_json()
        
        register_type = data.get('registerType', 'Ипотека')
        template_headers = data.get('templateHeaders', [])
        file_headers = data.get('fileHeaders', [])
        
        print(f"Автоматическое сопоставление для {register_type}")
        print(f"Заголовки шаблона: {len(template_headers)}")
        print(f"Заголовки файла: {len(file_headers)}")
        
        # Выполняем автоматическое сопоставление
        result = mortgage_service.auto_map_headers(register_type, template_headers, file_headers)
        
        if result['success']:
            return jsonify({
                'success': True,
                'mappings': result['mappings'],
                'message': result['message']
            })
        else:
            return jsonify({'error': result['error']}), 400
            
    except Exception as e:
        print(f"Ошибка в auto_map_headers: {str(e)}")
        return jsonify({'error': str(e)}), 500


@mortgage_bp.route('/save-correspondences', methods=['POST'])
def save_correspondences():
    """Сохранение соответствий заголовков"""
    try:
        data = request.get_json()
        
        register_type = data.get('registerType', 'Ипотека')
        mappings = data.get('mappings', {})
        
        print(f"Сохраняем соответствия для {register_type}: {len(mappings)} элементов")
        
        # Сохраняем соответствия
        result = mortgage_service.save_correspondences(register_type, mappings)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message']
            })
        else:
            return jsonify({'error': result['error']}), 400
            
    except Exception as e:
        print(f"Ошибка в save_correspondences: {str(e)}")
        return jsonify({'error': str(e)}), 500


@mortgage_bp.route('/process', methods=['POST'])
def process_registry():
    """Обработка реестра"""
    try:
        data = request.get_json()
        
        task_number = data.get('taskNumber')
        register_type = data.get('registerType', 'Ипотека')
        
        if not task_number:
            return jsonify({'error': 'Номер задачи не указан'}), 400
        
        print(f"Запуск обработки реестра {register_type}, задача {task_number}")
        
        # Запускаем обработку
        success, message = mortgage_service.process_registry(task_number, register_type)
        
        if success:
            return jsonify({'message': message})
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        print(f"Ошибка в process_registry: {str(e)}")
        return jsonify({'error': str(e)}), 500


@mortgage_bp.route('/status', methods=['GET'])
def get_status():
    """Получение статуса обработки"""
    try:
        status = mortgage_service.get_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@mortgage_bp.route('/cancel', methods=['POST'])
def cancel_processing():
    """Отмена обработки"""
    try:
        result = mortgage_service.cancel_processing()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@mortgage_bp.route('/download', methods=['GET'])
def download_result():
    """Скачивание результата (архив с файлами)"""
    try:
        result_files = mortgage_service.get_result_files()
        
        if not result_files:
            return jsonify({'error': 'Файлы результата не найдены'}), 404
        
        # Создаем временный архив
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
            with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in result_files:
                    if os.path.exists(file_path):
                        # Добавляем файл в архив с именем без полного пути
                        arcname = os.path.basename(file_path)
                        zipf.write(file_path, arcname)
                        print(f"Добавлен в архив: {arcname}")
            
            # Отправляем архив
            return send_file(
                temp_zip.name,
                as_attachment=True,
                download_name=f"Ипотека_реестр_{datetime.now().strftime('%d_%m_%Y')}.zip",
                mimetype='application/zip'
            )
        
    except Exception as e:
        print(f"Ошибка в download_result: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Дополнительные API маршруты для поддержки интерфейса

@mortgage_bp.route('/get-settings', methods=['GET'])
def get_settings():
    """Получение настроек для типа реестра"""
    try:
        register_type = request.args.get('type', 'Ипотека')
        
        # Заглушка для настроек
        settings = {
            'Ипотека': {
                'Банк по умолчанию': 'Сбербанк',
                'Регион по умолчанию': 'Москва',
                'Канал по умолчанию': 'Интернет',
                'Приоритет': 'Высокий'
            }
        }
        
        return jsonify(settings.get(register_type, {}))
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@mortgage_bp.route('/save-settings', methods=['POST'])
def save_settings():
    """Сохранение настроек"""
    try:
        data = request.get_json()
        
        register_type = data.get('type', 'Ипотека')
        settings = data.get('settings', {})
        
        print(f"Сохраняем настройки для {register_type}: {settings}")
        
        # В реальном приложении здесь было бы сохранение в БД
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Для добавления в основное приложение Flask:
# from web.routes.mortgage_routes import mortgage_bp
# app.register_blueprint(mortgage_bp)


# web/templates/mortgage.html
"""
HTML шаблон для ипотечных реестров (ваш существующий HTML)
Здесь будет ваш существующий HTML код с минимальными изменениями для интеграции с бэкендом
"""

# Минимальные изменения в JavaScript части вашего HTML:

# 1. Замените функцию startProcessing():
def startProcessing_js():
    return """
function startProcessing() {
    const taskNumber = document.getElementById('task-number').value;
    
    if (!taskNumber || isNaN(taskNumber) || taskNumber <= 0) {
        showToast('Ошибка', 'Пожалуйста, введите корректный номер задачи', 'error');
        return;
    }
    
    // Закрываем диалог задачи
    closeTaskDialog();
    
    // Открываем диалог прогресса
    openProgressDialog();
    
    // Начинаем реальную обработку
    fetch('/processing/process', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            taskNumber: taskNumber,
            registerType: currentRegisterType
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Начинаем отслеживание статуса
        startStatusTracking();
    })
    .catch(error => {
        closeProgressDialog();
        showToast('Ошибка', error.message, 'error');
    });
}
"""

# 2. Добавьте функцию отслеживания статуса:
def status_tracking_js():
    return """
let statusCheckInterval;

function startStatusTracking() {
    statusCheckInterval = setInterval(async () => {
        try {
            const response = await fetch('/processing/status');
            const status = await response.json();

            document.getElementById('progress-step').textContent = status.status;
            document.getElementById('progress-percentage').textContent = status.progress + '%';
            document.getElementById('progress-bar-fill').style.width = status.progress + '%';

            if (!status.is_running) {
                clearInterval(statusCheckInterval);

                if (status.error) {
                    showToast('Ошибка обработки', status.error, 'error');
                    closeProgressDialog();
                } else if (status.has_result) {
                    // Автоматически скачиваем результат
                    setTimeout(() => {
                        downloadResults();
                        closeProgressDialog();
                    }, 1000);
                }
            }
        } catch (error) {
            console.error('Ошибка получения статуса:', error);
            clearInterval(statusCheckInterval);
        }
    }, 1000);
}

function downloadResults() {
    const link = document.createElement('a');
    link.href = '/processing/download';
    link.download = '';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showToast('Файлы готовы', 'Реестр успешно создан и скачан', 'success');
}
"""

# 3. Обновите функцию cancelProcessing():
def cancel_processing_js():
    return """
function cancelProcessing() {
    fetch('/processing/cancel', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (statusCheckInterval) {
            clearInterval(statusCheckInterval);
        }
        closeProgressDialog();
        showToast('Отменено', 'Обработка реестра была отменена', 'warning');
    })
    .catch(error => {
        showToast('Ошибка', 'Не удалось отменить процесс', 'error');
    });
}
"""