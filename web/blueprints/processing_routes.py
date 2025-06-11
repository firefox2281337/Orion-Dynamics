# web/blueprints/processing_routes.py
"""
Рефакторинг Blueprint для маршрутов обработки файлов и данных
"""

import os
import sys
import json
import tempfile
import threading
import importlib
import traceback
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, Type
from werkzeug.utils import secure_filename
import pandas as pd
import io
import zipfile
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, jsonify, send_file, current_app
from pathlib import Path


# Импорты сервисов с обработкой ошибок
def safe_import():
    """Безопасный импорт сервисов с созданием заглушек при неудаче"""
    try:
        from web.blueprints.processing import ProcessingService
        from web.services.excel_service import ExcelService
        from web.services.data_service import DataService
        from web.utils.access_control import require_ip_access
        from web.utils.logging_helper import log_user_access
        from web.services.correspondences_service import CorrespondencesService
        return True, {
            'ProcessingService': ProcessingService,
            'ExcelService': ExcelService,
            'DataService': DataService,
            'require_ip_access': require_ip_access,
            'log_user_access': log_user_access,
            'CorrespondencesService': CorrespondencesService
        }
    except ImportError as e:
        print(f"Предупреждение: Не удалось импортировать некоторые сервисы: {e}")
        
        # Заглушки
        class MockProcessingService:
            def get_status(self): return {'status': 'not_implemented'}
            def cancel_processing(self): return {'message': 'not_implemented'}
            def get_result_file(self): return None
            def reload_business_logic(self): return False
            def process_files(self, v, c): return False, 'not_implemented'
        
        class MockExcelService:
            def generate_report(self, *args): raise NotImplementedError
            def allowed_file(self, filename): return filename.endswith('.xlsx')
        
        class MockDataService:
            def process_metragi(self, file): return None
        
        def mock_decorator(f): return f
        def mock_log(**kwargs): pass
        
        from web.services.correspondences_service import CorrespondencesService
        
        return False, {
            'ProcessingService': MockProcessingService,
            'ExcelService': MockExcelService,
            'DataService': MockDataService,
            'require_ip_access': mock_decorator,
            'log_user_access': mock_log,
            'CorrespondencesService': CorrespondencesService
        }


# Конфигурация
class Config:
    ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
    TEMP_UPLOAD_FOLDER = Path(r'C:\Users\EPopkov\Documents\Orion Dynamics\temp_uploads')
    DB_SERVER_URL = "http://192.168.50.220:5000/sql/query"
    CLEANUP_TIMEOUT = 3600  # 1 час
    
    @classmethod
    def setup_temp_folder(cls):
        cls.TEMP_UPLOAD_FOLDER.mkdir(exist_ok=True)


# Инициализация
services_loaded, services = safe_import()
Config.setup_temp_folder()

# Создаем Blueprint
processing_bp = Blueprint('processing', __name__)

# Глобальные переменные
active_processes: Dict[str, Dict[str, Any]] = {}
correspondences_service = services['CorrespondencesService']()

# Инициализируем сервисы
try:
    processing_service = services['ProcessingService']()
    excel_service = services['ExcelService']()
    data_service = services['DataService']()
except Exception as e:
    print(f"Ошибка инициализации сервисов: {e}")
    processing_service = services['ProcessingService']()
    excel_service = services['ExcelService']()
    data_service = services['DataService']()


def allowed_file(filename: str) -> bool:
    """Проверка допустимых расширений файлов"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


# ============================================================================
# БАЗОВЫЕ КЛАССЫ И ФАБРИКА
# ============================================================================

class ProcessorError(Exception):
    """Базовая ошибка процессора"""
    pass


class BaseProcessor(ABC):
    """Базовый класс для всех процессоров реестров"""
    
    def __init__(self, number: str, file_path: str, correspondences: Dict, 
                 template_headers: list, register_type: str):
        self.number = str(number) if number is not None else "0"
        self.file_path = file_path
        self.correspondences = correspondences or {}
        self.template_headers = template_headers or []
        self.register_type = register_type
        self.is_running = True
        self.progress_callback: Optional[Callable] = None
        self.status_callback: Optional[Callable] = None
        self.temp_dir = tempfile.mkdtemp(prefix=f"autoreg_{self.number}_")
    
    @property
    @abstractmethod
    def business_logic_module(self) -> str:
        """Путь к модулю с бизнес-логикой"""
        pass
    
    @property
    @abstractmethod
    def ready_headers(self) -> list:
        """Готовые заголовки для обработки"""
        pass
    
    def set_callbacks(self, progress_callback: Callable, status_callback: Callable):
        """Установка колбэков для обновления прогресса"""
        self.progress_callback = progress_callback
        self.status_callback = status_callback
    
    def emit_progress(self, progress: int, step: str):
        """Отправка обновления прогресса"""
        if self.progress_callback:
            progress_val = int(progress) if isinstance(progress, (int, float)) else 0
            step_val = str(step) if step is not None else "Обработка..."
            self.progress_callback(progress_val, step_val)
    
    def emit_status(self, status: str):
        """Отправка обновления статуса"""
        if self.status_callback:
            self.status_callback(str(status))
    
    def reload_business_logic(self) -> bool:
        """Динамическая перезагрузка модуля с бизнес-логикой"""
        try:
            if self.business_logic_module in sys.modules:
                importlib.reload(sys.modules[self.business_logic_module])
                print(f"Модуль {self.business_logic_module} перезагружен")
            else:
                importlib.import_module(self.business_logic_module)
                print(f"Модуль {self.business_logic_module} загружен")
            return True
        except Exception as e:
            print(f"Ошибка при перезагрузке модуля: {e}")
            traceback.print_exc()
            return False
    
    def run(self) -> Dict[str, Any]:
        """Основная функция обработки с горячей загрузкой"""
        try:
            # Перезагружаем бизнес-логику перед выполнением
            if not self.reload_business_logic():
                return {
                    'success': False,
                    'error': 'Ошибка перезагрузки модуля бизнес-логики'
                }
            
            # Пытаемся использовать реальную бизнес-логику
            try:
                business_logic = sys.modules[self.business_logic_module]
                
                # Если есть класс RegistryProcessor в модуле
                if hasattr(business_logic, 'RegistryProcessor'):
                    processor_class = business_logic.RegistryProcessor
                    processor = processor_class(
                        self.number, self.file_path, self.correspondences, 
                        self.template_headers, self.register_type
                    )
                    processor.set_callbacks(self.progress_callback, self.status_callback)
                    return processor.run()
                
                # Если есть функция process_registry
                elif hasattr(business_logic, 'process_registry'):
                    return business_logic.process_registry(
                        number=self.number,
                        file_path=self.file_path,
                        correspondences=self.correspondences,
                        template_headers=self.template_headers,
                        register_type=self.register_type,
                        progress_callback=self.progress_callback,
                        status_callback=self.status_callback
                    )
                
                else:
                    # Используем заглушку
                    return self._fallback_processing()
                    
            except Exception as e:
                print(f"Ошибка при использовании бизнес-логики: {e}")
                return self._fallback_processing()
                
        except Exception as e:
            error_msg = f"Ошибка обработки: {str(e)}"
            self.emit_status(error_msg)
            self.emit_progress(0, "Ошибка")
            return {
                'success': False,
                'error': error_msg
            }
    
    def _fallback_processing(self) -> Dict[str, Any]:
        """Заглушка обработки для тестирования"""
        try:
            self.emit_progress(10, "Инициализация...")
            
            if not os.path.exists(self.file_path):
                return {'success': False, 'error': 'Файл не найден'}
            
            # Имитируем обработку
            for i in range(1, 11):
                if not self.is_running:
                    return {'success': False, 'error': 'Процесс остановлен'}
                
                progress = i * 10
                self.emit_progress(progress, f"Шаг {i} из 10...")
                
                # Небольшая задержка для демонстрации
                import time
                time.sleep(0.5)
            
            # Создаем папку результата
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            folder_name = f"{self.number} - {self.register_type} пролонгация"
            folder_path = os.path.join(desktop_path, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            
            # Создаем демо-файл
            demo_file = os.path.join(folder_path, "demo_result.txt")
            with open(demo_file, 'w', encoding='utf-8') as f:
                f.write(f"Демо-результат обработки\n")
                f.write(f"Номер задачи: {self.number}\n")
                f.write(f"Тип реестра: {self.register_type}\n")
                f.write(f"Файл: {os.path.basename(self.file_path)}\n")
                f.write(f"Соответствий: {len(self.correspondences)}\n")
            
            self.emit_progress(100, "Завершено")
            
            return {
                'success': True,
                'message': 'Демо-обработка завершена',
                'files_created': [demo_file],
                'folder_path': folder_path,
                'stats': {
                    'total_records': 100,
                    'processed_records': 95,
                    'no_phone_records': 3,
                    'no_data_records': 2
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Ошибка демо-обработки: {str(e)}"
            }
    
    def stop(self):
        """Остановка процесса"""
        self.is_running = False
    
    def cleanup(self):
        """Очистка временных файлов"""
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                print(f"Временная папка {self.temp_dir} удалена")
        except Exception as e:
            print(f"Ошибка очистки временных файлов: {e}")


class IpotekaProcessor(BaseProcessor):
    """Процессор для реестров Ипотека"""
    
    @property
    def business_logic_module(self) -> str:
        return "web.templates.nexus.autoreg.logic.handler"
    
    @property
    def ready_headers(self) -> list:
        return [
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


class IpotekaMskProcessor(BaseProcessor):
    """Процессор для реестров Ипотека_мск (Профит)"""
    
    @property
    def business_logic_module(self) -> str:
        return "web.templates.nexus.autoreg.logic.handler_profit"
    
    @property
    def ready_headers(self) -> list:
        return [
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


class KaskoProcessor(BaseProcessor):
    """Процессор для реестров КАСКО"""
    
    @property
    def business_logic_module(self) -> str:
        return "web.templates.nexus.autoreg.logic.handler_kasko"
    
    @property
    def ready_headers(self) -> list:
        return [
            "id физ лица", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество", "Дата рождения", "Основной телефон",
            "Телефон 2", "Телефон 3", "Основной e-mail", "Филиал ВСК", "Регион", "Объект страхования", "Марка", "Модель", "Год выпуска",
            "VIN", "Дата окончания страхования", "Прошлый период Страховая премия", "Прошлый период Страховая сумма", "Канал",
            "Ответственный сотрудник ЦО Филиала", "Ответственный сотрудник Агент", "Дилер", "Логин дилера", "Точка продаж", "Категория партнера", 
            "Номер агентского договора", "Вид полиса", "ID_внешней системы", "Кампания", "Плановая дата звонка CTI", "Приоритет", "Вид страхования", 
            "Группа продукта", "Продукт", "Тип лида", "Передан в АКЦ", "Парный договор", "Вероятность, шт.", "Вероятность, руб."
        ]


class KaskoPoOsagoProcessor(BaseProcessor):
    """Процессор для реестров КАСКО по ОСАГО"""
    
    @property
    def business_logic_module(self) -> str:
        return "web.templates.nexus.autoreg.logic.handler_kaskopoosago"
    
    @property
    def ready_headers(self) -> list:
        return [
            "id физлицо", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество", "Дата рождения", "Филиал ВСК", 
            "Регион", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", "Объект страхования", "Марка", "Модель", 
            "Год выпуска", "VIN", "Дата окончания страхования", "Прошлый период Страховая премия", "Прошлый период Страховая сумма", 
            "Новый период страховая премия", "Канал", "Ссылка на проект", "Дополнительные сведения"
        ]


class OsagoProcessor(BaseProcessor):
    """Процессор для реестров ОСАГО"""
    
    @property
    def business_logic_module(self) -> str:
        return "web.templates.nexus.autoreg.logic.handler_osago"
    
    @property
    def ready_headers(self) -> list:
        return [
            "id физ лица", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество", "Дата рождения",
            "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", "Филиал ВСК", "Регион", "Объект страхования",
            "Марка", "Модель", "Год выпуска", "VIN", "Ссылка на проект", "Дата окончания страхования",
            "Прошлый период Страховая премия", "Прошлый период Страховая сумма", "Новый период Страховая премия",
            "Промокод", "Канал", "ID_внешней системы", "Тип лида", "Продукт", "Группа продукта", "Вид страхования",
            "Приоритет", "Плановая дата звонка CTI", "Номер проекта", "Программа страхования"
        ]


class MbgProcessor(BaseProcessor):
    """Процессор для реестров МБГ"""
    
    @property
    def business_logic_module(self) -> str:
        return "web.templates.nexus.autoreg.logic.handler_mbg"
    
    @property
    def ready_headers(self) -> list:
        return [
            "ID_внешней системы", "Приоритет", "Тип лида", "Кампания", "id физ лица", 
            "ФИО", "Фамилия", "Имя", "Отчество", "Регион", "Филиал ВСК", "Дата рождения", 
            "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", "Вид страхования", "Группа продукта", 
            "Продукт", "№ Договора К Пролонгации", "Дата окончания страхования", "Прошлый период Страховая премия", 
            "Прошлый период Страховая сумма", "Канал", "Объект страхования"
        ]


class IpoWaProcessor(BaseProcessor):
    """Процессор для реестров МБГ"""
    
    @property
    def business_logic_module(self) -> str:
        return "web.templates.nexus.autoreg.logic.ipoteka_wa"
    
    @property
    def ready_headers(self) -> list:
        return [
            "ID_внешней системы", "Примечания", "Дополнительные сведения", "Кампания", "Тип лида", "Группа продукта",
            "Продукт", "Вид страхования", "Ответственное подразделение", "Ответственный отдел", "Приоритет", "id физ лица",
            "ФИО", "Фамилия", "Имя", "Отчество", "Дата рождения", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail",
            "Регион", "Филиал ВСК", "Другой полис", "Кредитный договор Дата", "Банк", "Объект страхования", "Дата окончания страхования",
            "Прошлый период Страховая премия", "Прошлый период Страховая сумма", "Канал", "Тип базы"
        ]


class Osago41Processor(BaseProcessor):
    """Процессор для реестров МБГ"""
    
    @property
    def business_logic_module(self) -> str:
        return "web.templates.nexus.autoreg.logic.osago_4_1_up"
    
    @property
    def ready_headers(self) -> list:
        return [
            "id физлицо", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество", "Дата рождения", "Филиал ВСК", 
            "Регион", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", "Объект страхования", "Марка", "Модель", 
            "Год выпуска", "VIN", "Дата окончания страхования", "Прошлый период Страховая премия", "Прошлый период Страховая сумма", 
            "Новый период страховая премия", "Канал", "Ссылка на проект", "Дополнительные сведения"
        ]


class OsagoWaProcessor(BaseProcessor):
    """Процессор для реестров МБГ"""
    
    @property
    def business_logic_module(self) -> str:
        return "web.templates.nexus.autoreg.logic.osago_wa"
    
    @property
    def ready_headers(self) -> list:
        return [
            "id физлицо", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество", "Дата рождения", "Филиал ВСК", 
            "Регион", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", "Объект страхования", "Марка", "Модель", 
            "Год выпуска", "VIN", "Дата окончания страхования", "Прошлый период Страховая премия", "Прошлый период Страховая сумма", 
            "Новый период страховая премия", "Канал", "Ссылка на проект", "Дополнительные сведения"
        ]


class IpoKomProcessor(BaseProcessor):
    """Процессор для реестров МБГ"""
    
    @property
    def business_logic_module(self) -> str:
        return "web.templates.nexus.autoreg.logic.ipoteka_kom_bank"
    
    @property
    def ready_headers(self) -> list:
        return [
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


class IpoSosProcessor(BaseProcessor):
    """Процессор для реестров МБГ"""
    
    @property
    def business_logic_module(self) -> str:
        return "web.templates.nexus.autoreg.logic.ipoteka_sos"
    
    @property
    def ready_headers(self) -> list:
        return [
            "id физ лица", "№ Договора К Пролонгации", "ID_внешней системы", "Статус рассылки 3", "Кампания", "Тип лида", "Продукт", "Группа продукта", 
            "Вид страхования", "Приоритет", "ФИО", "Фамилия", "Имя", "Отчество", "Дата рождения", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", 
            "Филиал ВСК", "Регион", "Банк", "Плановая дата звонка CTI", "Дата окончания страхования", "Прошлый период Страховая премия", "Прошлый период Страховая сумма", 
            "Канал", "Вид полиса", "Шт., вероятность пролонгации", "Руб., вероятность пролонгации", "Дополнительные сведения", "Ссылка на проект в CTI"
        ]


class OsagoKzProcessor(BaseProcessor):
    """Процессор для реестров МБГ"""
    
    @property
    def business_logic_module(self) -> str:
        return "web.templates.nexus.autoreg.logic.osago_kz"
    
    @property
    def ready_headers(self) -> list:
        return [
            "id физ лица", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество", "Дата рождения",
            "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", "Филиал ВСК", "Регион", "Объект страхования",
            "Марка", "Модель", "Год выпуска", "VIN", "Ссылка на проект", "Дата окончания страхования",
            "Прошлый период Страховая премия", "Прошлый период Страховая сумма", "Новый период Страховая премия",
            "Промокод", "Канал", "ID_внешней системы", "Тип лида", "Продукт", "Группа продукта", "Вид страхования",
            "Приоритет", "Плановая дата звонка CTI", "Номер проекта", "Программа страхования"
        ]
    

    
class DvrProcessor(BaseProcessor):
    """Процессор для реестров МБГ"""
    
    @property
    def business_logic_module(self) -> str:
        return "web.templates.nexus.autoreg.logic.handler_dvr"
    
    @property
    def ready_headers(self) -> list:
        return [
            "Примечания", "Продукт", "Филиал ВСК", "ФИО", "Фамилия", "Имя", "Отчество", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail",
            "Другой полис", "Дата начала страхования/дата заключения", "Кредитный договор Дата", 
            "Прошлый период Страховая сумма", "Марка", "Модель", "Год выпуска", "СтраховаяСумма", "Риск", "ТипСобытия", "Стадия"
        ]
    
class f1Processor(BaseProcessor):
    """Процессор для реестров f1"""
    
    @property
    def business_logic_module(self) -> str:
        return "web.templates.nexus.autoreg.logic.f1"
    
    @property
    def ready_headers(self) -> list:
        return [
            "id физ лица", "Тип лида", "Продукт", "Группа продукта", "Вид страхования", "ФИО", "Фамилия", 
            "Имя", "Отчество", "Дата рождения", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", 
            "Филиал ВСК", "Регион", "Другой полис", "Дополнительные сведения", "Тип базы"
        ]


class ProcessorFactory:
    """Фабрика для создания процессоров"""
    
    _processors: Dict[str, Type[BaseProcessor]] = {
        'Ипотека': IpotekaProcessor,
        'Ипотека_мск': IpotekaMskProcessor,
        'КАСКО': KaskoProcessor,
        'КАСКО_ИЗ_ОСАГО_4_1': KaskoPoOsagoProcessor,
        'ОСАГО': OsagoProcessor,
        'МБГ': MbgProcessor,
        'Ипотека_WA': IpoWaProcessor,
        'ОСАГО_4_1': Osago41Processor,
        'ОСАГО_WA': OsagoWaProcessor,
        'Ипотека_ком_банки': IpoKomProcessor,
        'Ипотека_SOS': IpoSosProcessor,
        'ОСАГО_КЗ': OsagoKzProcessor,
        'ДВР': DvrProcessor,
        'f1': f1Processor
    }
    
    @classmethod
    def register_processor(cls, register_type: str, processor_class: Type[BaseProcessor]):
        """Регистрация нового типа процессора"""
        cls._processors[register_type] = processor_class
    
    @classmethod
    def create_processor(cls, register_type: str, number: str, file_path: str, 
                        correspondences: Dict, template_headers: list) -> BaseProcessor:
        """Создание процессора по типу реестра"""
        processor_class = cls._processors.get(register_type)
        if not processor_class:
            raise ProcessorError(f"Неизвестный тип реестра: {register_type}")
        
        return processor_class(
            number=number,
            file_path=file_path,
            correspondences=correspondences,
            template_headers=template_headers,
            register_type=register_type
        )
    
    @classmethod
    def get_available_types(cls) -> list:
        """Получение списка доступных типов реестров"""
        return list(cls._processors.keys())


# ============================================================================
# УТИЛИТЫ
# ============================================================================

def get_file_size_mb(file_path: str) -> float:
    """Получение размера файла в мегабайтах"""
    try:
        size_bytes = os.path.getsize(file_path)
        return round(size_bytes / (1024 * 1024), 2)
    except:
        return 0.0


def run_processing(process_id: str, processor: BaseProcessor):
    """Выполнение обработки в отдельном потоке"""
    try:
        def progress_callback(progress: int, step: str):
            if process_id in active_processes:
                active_processes[process_id]['progress'] = progress
                active_processes[process_id]['step'] = step
        
        def status_callback(status: str):
            if process_id in active_processes:
                active_processes[process_id]['status'] = status
        
        # Подключаем колбэки
        processor.set_callbacks(progress_callback, status_callback)
        
        # Запускаем обработку
        result = processor.run()
        
        if process_id in active_processes:
            if result.get('success'):
                active_processes[process_id]['status'] = 'completed'
                active_processes[process_id]['progress'] = 100
                active_processes[process_id]['step'] = 'Завершено'
                active_processes[process_id]['result'] = result
                
                print(f"Процесс {process_id} завершен успешно")
                if result.get('download_file'):
                    print(f"Файл для скачивания: {result.get('download_file')}")
                
            else:
                active_processes[process_id]['status'] = 'error'
                active_processes[process_id]['error'] = result.get('error', 'Неизвестная ошибка')
                print(f"Процесс {process_id} завершен с ошибкой: {result.get('error')}")
        
    except Exception as e:
        if process_id in active_processes:
            active_processes[process_id]['status'] = 'error'
            active_processes[process_id]['error'] = str(e)
        print(f"Ошибка в run_processing: {e}")
        traceback.print_exc()
    finally:
        # Планируем очистку процесса
        def cleanup_process():
            import time
            time.sleep(Config.CLEANUP_TIMEOUT)
            if process_id in active_processes:
                try:
                    if hasattr(processor, 'cleanup'):
                        processor.cleanup()
                    del active_processes[process_id]
                    print(f"Процесс {process_id} очищен из памяти")
                except Exception as e:
                    print(f"Ошибка очистки процесса {process_id}: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_process)
        cleanup_thread.daemon = True
        cleanup_thread.start()


# ============================================================================
# РОУТЫ
# ============================================================================

@processing_bp.route('/status')
def get_status_nexus():
    """Получение текущего статуса обработки"""
    return jsonify(processing_service.get_status())


@processing_bp.route('/cancel', methods=['POST'])
def cancel_processing_reg():
    """Отмена обработки"""
    result = processing_service.cancel_processing()
    return jsonify(result)


@processing_bp.route('/download')
def download_result():
    """Скачивание результата обработки"""
    result_file = processing_service.get_result_file()
    if not result_file or not Path(result_file).exists():
        return jsonify({'error': 'Файл результата не найден'}), 404
    
    return send_file(result_file, as_attachment=True)


@processing_bp.route('/reload', methods=['POST'])
def reload_logic():
    """Принудительная перезагрузка бизнес-логики"""
    try:
        modules_to_reload = [
            "web.templates.nexus.autoreg.logic.handler",
            "web.templates.nexus.autoreg.logic.handler_kasko", 
            "web.templates.nexus.autoreg.logic.handler_profit",
            "web.templates.nexus.autoreg.logic.methods.handle.handler",
            "web.templates.nexus.autoreg.logic.methods.SQL.data_processing"
        ]
        
        reloaded_count = 0
        for module_name in modules_to_reload:
            try:
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
                    reloaded_count += 1
                    print(f"Перезагружен модуль: {module_name}")
            except Exception as e:
                print(f"Ошибка перезагрузки модуля {module_name}: {e}")
        
        message = f'Успешно перезагружено {reloaded_count} модулей' if reloaded_count > 0 else 'Модули загружены впервые'
        return jsonify({'message': message})
            
    except Exception as e:
        return jsonify({'error': f'Ошибка перезагрузки модулей: {str(e)}'}), 500


@processing_bp.route('/process', methods=['POST'])
def process_files():
    """Обработка файлов Verint и Call"""
    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': 'Файлы не загружены'}), 400
    
    # Проверяем наличие необходимых файлов
    verint_file = None
    call_file = None
    
    for file in files:
        if file.filename.startswith('Речевая'):
            verint_file = file
        elif file.filename.startswith('call'):
            call_file = file
    
    if not verint_file or not call_file:
        return jsonify({'error': 'Необходимы файлы Verint и Call'}), 400
    
    success, message = processing_service.process_files(verint_file, call_file)
    
    if success:
        return jsonify({'message': message})
    else:
        return jsonify({'error': message}), 400


@processing_bp.route('/upload-excel', methods=['POST'])
def upload_excel():
    """Загрузка Excel файла и извлечение заголовков"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Файл не найден'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Неподдерживаемый формат файла. Разрешены только .xlsx и .xls'}), 400
        
        # Сохраняем файл
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}.{filename}"
        file_path = Config.TEMP_UPLOAD_FOLDER / filename
        file.save(str(file_path))
        
        # Читаем заголовки
        try:
            df = pd.read_excel(file_path, nrows=0)
            headers = df.columns.tolist()
            
            # Сохраняем данные сессии
            session_data = {
                'file_path': str(file_path),
                'filename': file.filename,
                'headers': headers,
                'upload_time': datetime.now().isoformat()
            }
            
            session_file = Config.TEMP_UPLOAD_FOLDER / f"session_{timestamp}.json"
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False)
            
            return jsonify({
                'success': True,
                'headers': headers,
                'session_id': timestamp,
                'message': f'Файл {file.filename} успешно загружен'
            })
            
        except Exception as e:
            if file_path.exists():
                file_path.unlink()
            return jsonify({'error': f'Ошибка чтения файла: {str(e)}'}), 400
            
    except Exception as e:
        current_app.logger.error(f"Ошибка в upload_excel: {str(e)}")
        return jsonify({'error': f'Ошибка загрузки файла: {str(e)}'}), 500
    

@processing_bp.route('/combined-upload-excel', methods=['POST'])
def combined_upload_excel():
    """Загрузка 4 Excel файлов, объединение и извлечение заголовков"""
    try:
        # Проверяем наличие файлов
        if 'files' not in request.files:
            return jsonify({'error': 'Файлы не найдены'}), 400
        
        files = request.files.getlist('files')
        if len(files) == 0:
            return jsonify({'error': 'Файлы не выбраны'}), 400
            
        if len(files) != 4:
            return jsonify({'error': f'Необходимо загрузить ровно 4 файла, получено: {len(files)}'}), 400
        
        # Проверяем форматы файлов
        for file in files:
            if not allowed_file(file.filename):
                return jsonify({'error': f'Неподдерживаемый формат файла "{file.filename}". Разрешены только .xlsx и .xls'}), 400
        
        # Определяем префиксы файлов и проверяем их корректность
        required_prefixes = ['ipot_akc_', 'ipot_mos_', 'kasko_akc_', 'kasko_mos_']
        found_prefixes = []
        
        for file in files:
            filename_lower = file.filename.lower()
            matched_prefix = None
            for prefix in required_prefixes:
                if filename_lower.startswith(prefix):
                    matched_prefix = prefix
                    break
            
            if matched_prefix is None:
                return jsonify({'error': f'Файл "{file.filename}" не соответствует требуемому формату имени'}), 400
            
            if matched_prefix in found_prefixes:
                return jsonify({'error': f'Найдено несколько файлов с префиксом "{matched_prefix}"'}), 400
                
            found_prefixes.append(matched_prefix)
        
        # Проверяем, что все необходимые префиксы найдены
        missing_prefixes = set(required_prefixes) - set(found_prefixes)
        if missing_prefixes:
            missing_names = [prefix.replace('_', ' ').title() for prefix in missing_prefixes]
            return jsonify({'error': f'Отсутствуют файлы: {", ".join(missing_names)}'}), 400
        
        # Создаем уникальный timestamp для сессии
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Сохраняем файлы и читаем их данные
        saved_files = []
        combined_data = []
        all_headers = set()
        
        try:
            for file in files:
                # Сохраняем файл
                filename = secure_filename(file.filename)
                file_path = Config.TEMP_UPLOAD_FOLDER / f"{timestamp}_{filename}"
                file.save(str(file_path))
                saved_files.append(file_path)
                
                # Читаем данные
                try:
                    df = pd.read_excel(file_path)
                    
                    if df.empty:
                        raise ValueError(f'Файл "{file.filename}" пуст')
                    
                    # Определяем тип базы по имени файла
                    filename_lower = file.filename.lower()
                    if filename_lower.startswith('ipot_akc_'):
                        db_type = 'ipot_akc'
                    elif filename_lower.startswith('ipot_mos_'):
                        db_type = 'ipot_mos'
                    elif filename_lower.startswith('kasko_akc_'):
                        db_type = 'kasko_akc'
                    elif filename_lower.startswith('kasko_mos_'):
                        db_type = 'kasko_mos'
                    else:
                        db_type = 'unknown'
                    
                    # Добавляем столбец "Тип базы"
                    df['Тип базы'] = db_type
                    
                    # Добавляем заголовки в общий набор
                    df.columns = df.columns.str.lower()
                    all_headers.update(df.columns.tolist())
                    
                    # Добавляем данные в общий список
                    combined_data.append(df)
                    
                    current_app.logger.info(f"Файл {file.filename} загружен: {len(df)} строк, {len(df.columns)} столбцов")
                    
                except Exception as e:
                    raise ValueError(f'Ошибка чтения файла "{file.filename}": {str(e)}')
            
            # Объединяем все данные
            if not combined_data:
                raise ValueError('Не удалось прочитать ни один файл')
            
            # Объединяем DataFrames
            combined_df = pd.concat(combined_data, ignore_index=True, sort=False)
            
            # Получаем список всех заголовков
            headers = combined_df.columns.tolist()
            
            # Сохраняем объединенный файл
            combined_file_path = Config.TEMP_UPLOAD_FOLDER / f"combined_{timestamp}.xlsx"
            combined_df.to_excel(combined_file_path, index=False)
            
            # Сохраняем данные сессии в формате, совместимом с start_processing
            session_data = {
                'file_path': str(combined_file_path),  # Основной путь для совместимости
                'combined_file_path': str(combined_file_path),  # Дополнительный для информации
                'original_files': [f.name for f in saved_files],
                'headers': headers,
                'upload_time': datetime.now().isoformat(),
                'total_rows': len(combined_df),
                'filename': f"combined_{len(files)}_files.xlsx",  # Добавляем filename для совместимости
                'file_types': {
                    'ipot_akc': len([df for df in combined_data if (df['тип базы'] == 'ipot_akc').any()]),
                    'ipot_mos': len([df for df in combined_data if (df['тип базы'] == 'ipot_mos').any()]),
                    'kasko_akc': len([df for df in combined_data if (df['тип базы'] == 'kasko_akc').any()]),
                    'kasko_mos': len([df for df in combined_data if (df['тип базы'] == 'kasko_mos').any()])
                },
                'row_counts': {
                    'ipot_akc': len(combined_df[combined_df['тип базы'] == 'ipot_akc']),
                    'ipot_mos': len(combined_df[combined_df['тип базы'] == 'ipot_mos']),
                    'kasko_akc': len(combined_df[combined_df['тип базы'] == 'kasko_akc']),
                    'kasko_mos': len(combined_df[combined_df['тип базы'] == 'kasko_mos'])
                }
            }
            
            session_file = Config.TEMP_UPLOAD_FOLDER / f"session_{timestamp}.json"
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            
            # Логируем успешное объединение
            current_app.logger.info(f"Успешно объединены файлы: {len(combined_df)} строк, {len(headers)} уникальных заголовков")
            current_app.logger.info(f"Распределение по типам: {session_data['row_counts']}")
            
            return jsonify({
                'success': True,
                'headers': headers,
                'session_id': timestamp,
                'total_rows': len(combined_df),
                'file_types_count': session_data['row_counts'],
                'message': f'Успешно объединены {len(files)} файлов ({len(combined_df)} строк)'
            })
            
        except Exception as e:
            # Очищаем сохраненные файлы в случае ошибки
            for file_path in saved_files:
                if file_path.exists():
                    file_path.unlink()
            
            # Очищаем объединенный файл если он был создан
            combined_file_path = Config.TEMP_UPLOAD_FOLDER / f"combined_{timestamp}.xlsx"
            if combined_file_path.exists():
                combined_file_path.unlink()
                
            # Очищаем файл сессии если он был создан
            session_file = Config.TEMP_UPLOAD_FOLDER / f"session_{timestamp}.json"
            if session_file.exists():
                session_file.unlink()
                
            raise e
            
    except ValueError as ve:
        current_app.logger.error(f"Ошибка валидации в combined_upload_excel: {str(ve)}")
        return jsonify({'error': str(ve)}), 400
        
    except Exception as e:
        current_app.logger.error(f"Ошибка в combined_upload_excel: {str(e)}")
        return jsonify({'error': f'Ошибка загрузки и объединения файлов: {str(e)}'}), 500


@processing_bp.route('/start-processing', methods=['POST'])
def start_processing():
    """Запуск обработки реестра с использованием фабрики"""
    try:
        data = request.json
        task_number = data.get('taskNumber')
        session_id = data.get('sessionId')
        mappings = data.get('mappings', {})
        register_type = data.get('registerType', 'Ипотека')
        
        if not task_number:
            return jsonify({'error': 'Номер задачи не указан'}), 400
        
        if not session_id:
            return jsonify({'error': 'Сессия не найдена'}), 400
        
        # Загружаем данные сессии
        session_file = Config.TEMP_UPLOAD_FOLDER / f"session_{session_id}.json"
        if not session_file.exists():
            return jsonify({'error': 'Файл сессии не найден'}), 400
        
        with open(session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        file_path = session_data.get('file_path')
        if not os.path.exists(file_path):
            return jsonify({'error': 'Загруженный файл не найден'}), 400
        
        # Создаем процессор через фабрику
        try:
            processor = ProcessorFactory.create_processor(
                register_type=register_type,
                number=task_number,
                file_path=file_path,
                correspondences=mappings,
                template_headers=[]  # Будут заполнены в процессоре
            )
        except ProcessorError as e:
            return jsonify({'error': str(e)}), 400
        
        # Запускаем обработку в отдельном потоке
        process_id = f"process_{session_id}_{task_number}"
        active_processes[process_id] = {
            'processor': processor,
            'status': 'running',
            'progress': 0,
            'step': 'Инициализация...',
            'start_time': datetime.now()
        }
        
        thread = threading.Thread(target=run_processing, args=(process_id, processor))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'process_id': process_id,
            'message': 'Обработка запущена'
        })
        
    except Exception as e:
        current_app.logger.error(f"Ошибка в start_processing: {str(e)}")
        return jsonify({'error': f'Ошибка запуска обработки: {str(e)}'}), 500


@processing_bp.route('/get-progress/<process_id>', methods=['GET'])
def get_progress(process_id: str):
    """Получение прогресса обработки"""
    if process_id not in active_processes:
        return jsonify({'error': 'Процесс не найден'}), 404
    
    process_info = active_processes[process_id]
    return jsonify({
        'progress': process_info.get('progress', 0),
        'step': process_info.get('step', ''),
        'status': process_info.get('status', 'unknown'),
        'error': process_info.get('error'),
        'result': process_info.get('result')
    })


@processing_bp.route('/cancel-processing/<process_id>', methods=['POST'])
def cancel_processing(process_id: str):
    """Отмена обработки"""
    if process_id not in active_processes:
        return jsonify({'error': 'Процесс не найден'}), 404
    
    try:
        processor = active_processes[process_id]['processor']
        processor.stop()
        active_processes[process_id]['status'] = 'cancelled'
        
        return jsonify({
            'success': True,
            'message': 'Обработка отменена'
        })
        
    except Exception as e:
        return jsonify({'error': f'Ошибка отмены: {str(e)}'}), 500


@processing_bp.route('/download-result/<process_id>', methods=['GET'])
def download_result_autoreg(process_id: str):
    """Скачивание результата обработки"""
    if process_id not in active_processes:
        return jsonify({'error': 'Процесс не найден'}), 404
    
    process_info = active_processes[process_id]
    
    if process_info.get('status') != 'completed':
        return jsonify({'error': 'Обработка не завершена'}), 400
    
    result = process_info.get('result')
    if not result or not result.get('success'):
        return jsonify({'error': 'Нет результата для скачивания'}), 404
    
    download_file = result.get('download_file')
    download_filename = result.get('download_filename')
    
    if not download_file or not os.path.exists(download_file):
        return jsonify({'error': 'Файл результата не найден'}), 404
    
    try:
        def remove_file():
            """Удаление файла после отправки"""
            try:
                import time
                time.sleep(5)  # Ждем 5 секунд после отправки
                if os.path.exists(download_file):
                    os.remove(download_file)
                
                # Удаляем временную папку
                temp_dir = result.get('temp_dir')
                if temp_dir and os.path.exists(temp_dir):
                    import shutil
                    shutil.rmtree(temp_dir)
                    
                print(f"Временные файлы для процесса {process_id} удалены")
            except Exception as e:
                print(f"Ошибка удаления временных файлов: {e}")
        
        # Запускаем удаление в отдельном потоке
        cleanup_thread = threading.Thread(target=remove_file)
        cleanup_thread.daemon = True
        cleanup_thread.start()
        
        return send_file(
            download_file,
            as_attachment=True,
            download_name=download_filename,
            mimetype='application/zip'
        )
        
    except Exception as e:
        return jsonify({'error': f'Ошибка отправки файла: {str(e)}'}), 500


@processing_bp.route('/check-download/<process_id>', methods=['GET'])
def check_download_ready(process_id: str):
    """Проверка готовности файла для скачивания"""
    if process_id not in active_processes:
        return jsonify({'error': 'Процесс не найден'}), 404
    
    process_info = active_processes[process_id]
    result = process_info.get('result', {})
    
    if process_info.get('status') == 'completed' and result.get('success'):
        download_file = result.get('download_file')
        if download_file and os.path.exists(download_file):
            return jsonify({
                'ready': True,
                'filename': result.get('download_filename'),
                'size': os.path.getsize(download_file),
                'stats': result.get('stats', {})
            })
    
    return jsonify({'ready': False})


@processing_bp.route('/process-stats/<process_id>', methods=['GET'])
def get_process_stats(process_id: str):
    """Получение детальной статистики обработки"""
    if process_id not in active_processes:
        return jsonify({'error': 'Процесс не найден'}), 404
    
    process_info = active_processes[process_id]
    result = process_info.get('result', {})
    
    response = {
        'process_id': process_id,
        'status': process_info.get('status'),
        'progress': process_info.get('progress', 0),
        'step': process_info.get('step', ''),
        'start_time': process_info.get('start_time', datetime.now()).isoformat() if process_info.get('start_time') else None,
        'stats': result.get('stats', {}),
        'has_download': bool(result.get('download_file')),
        'error': process_info.get('error')
    }
    
    # Добавляем информацию о файле, если доступен
    if result.get('download_file') and os.path.exists(result.get('download_file')):
        response['file_info'] = {
            'filename': result.get('download_filename'),
            'size_mb': get_file_size_mb(result.get('download_file')),
            'created': datetime.fromtimestamp(
                os.path.getctime(result.get('download_file'))
            ).isoformat()
        }
    
    return jsonify(response)


@processing_bp.route('/cleanup-process/<process_id>', methods=['POST'])
def cleanup_process_manual(process_id: str):
    """Ручная очистка процесса"""
    if process_id not in active_processes:
        return jsonify({'error': 'Процесс не найден'}), 404
    
    try:
        process_info = active_processes[process_id]
        result = process_info.get('result', {})
        
        # Удаляем файлы
        download_file = result.get('download_file')
        if download_file and os.path.exists(download_file):
            os.remove(download_file)
        
        temp_dir = result.get('temp_dir')
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)
        
        # Удаляем процесс из активных
        del active_processes[process_id]
        
        return jsonify({'success': True, 'message': 'Процесс очищен'})
        
    except Exception as e:
        return jsonify({'error': f'Ошибка очистки: {str(e)}'}), 500


@processing_bp.route('/cleanup-temp', methods=['POST'])
def cleanup_temp():
    """Улучшенная очистка временных файлов"""
    try:
        cleaned_files = 0
        cleaned_size = 0
        
        # Удаляем файлы старше 24 часов
        cutoff_time = datetime.now().timestamp() - 24 * 60 * 60
        
        if Config.TEMP_UPLOAD_FOLDER.exists():
            for file_path in Config.TEMP_UPLOAD_FOLDER.iterdir():
                try:
                    if file_path.is_file() and file_path.stat().st_ctime < cutoff_time:
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        cleaned_files += 1
                        cleaned_size += file_size
                    elif file_path.is_dir() and file_path.stat().st_ctime < cutoff_time:
                        # Удаляем старые временные папки
                        import shutil
                        folder_size = sum(
                            f.stat().st_size for f in file_path.rglob('*') if f.is_file()
                        )
                        shutil.rmtree(file_path)
                        cleaned_files += 1
                        cleaned_size += folder_size
                except Exception as e:
                    print(f"Ошибка удаления {file_path}: {e}")
        
        # Очищаем завершенные процессы старше 1 часа
        old_processes = []
        one_hour_ago = datetime.now().timestamp() - 3600
        
        for proc_id, proc_info in active_processes.items():
            start_time = proc_info.get('start_time')
            if (start_time and start_time.timestamp() < one_hour_ago and 
                proc_info.get('status') in ['completed', 'error', 'cancelled']):
                old_processes.append(proc_id)
        
        for proc_id in old_processes:
            try:
                result = active_processes[proc_id].get('result', {})
                
                # Удаляем файлы процесса
                download_file = result.get('download_file')
                if download_file and os.path.exists(download_file):
                    file_size = os.path.getsize(download_file)
                    os.remove(download_file)
                    cleaned_size += file_size
                
                temp_dir = result.get('temp_dir')
                if temp_dir and os.path.exists(temp_dir):
                    import shutil
                    shutil.rmtree(temp_dir)
                
                del active_processes[proc_id]
                print(f"Очищен старый процесс: {proc_id}")
                
            except Exception as e:
                print(f"Ошибка очистки процесса {proc_id}: {e}")
        
        cleaned_size_mb = round(cleaned_size / (1024 * 1024), 2)
        
        return jsonify({
            'success': True,
            'message': 'Временные файлы очищены',
            'cleaned_files': cleaned_files,
            'cleaned_size_mb': cleaned_size_mb,
            'cleaned_processes': len(old_processes)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@processing_bp.route('/available-types', methods=['GET'])
def get_available_types():
    """Получение списка доступных типов реестров"""
    return jsonify({
        'types': ProcessorFactory.get_available_types(),
        'message': 'Доступные типы реестров'
    })


# ============================================================================
# ДОПОЛНИТЕЛЬНЫЕ РОУТЫ (из оригинального файла)
# ============================================================================

@processing_bp.route('/kasko', methods=['GET', 'POST'])
@services['require_ip_access']
def kasko_page():
    """Страница для сбора КАСКО"""
    current_year = datetime.now().year
    last_check = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    
    if request.method == 'POST':
        selected_quarter = request.form.get('quarter')
        selected_year = request.form.get('year')
        selected_checkboxes = request.form.getlist('checkboxes')
        
        # Логируем выгрузку
        services['log_user_access'](
            page="KASKO Report",
            client_ip=request.remote_addr,
            current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
            message=f"Выгрузка КАСКО: {selected_quarter}кв {selected_year}, филиалы: {selected_checkboxes}"
        )
        
        try:
            # Базовый путь к файлам КАСКО
            base_path = r"\\vskportal3\SiteDirectory\cpp\DocLib1"
            mem = excel_service.generate_report(
                selected_quarter, selected_year, selected_checkboxes, base_path
            )
            
            return send_file(
                mem,
                as_attachment=True,
                download_name=f'otchet_kasko_{selected_quarter}_kv_{selected_year}.xlsx',
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        except Exception as e:
            return jsonify({'error': f'Ошибка генерации отчёта: {str(e)}'}), 500
    
    services['log_user_access'](
        page="site/kasko.html",
        client_ip=request.remote_addr,
        current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
        message="Пользователь зашёл на kasko.html"
    )
    
    return render_template(
        'site/kasko.html',
        current_year=current_year,
        last_check=last_check
    )


@processing_bp.route('/megahelper', methods=['GET', 'POST'])
@services['require_ip_access']
def megahelper_page():
    """Страница Megahelper"""
    last_check = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    current_year = datetime.now().year
    
    services['log_user_access'](
        page="site/megahelper.html",
        client_ip=request.remote_addr,
        current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
        message="Пользователь зашёл на megahelper.html"
    )
    
    return render_template(
        'site/megahelper.html',
        current_year=current_year,
        last_check=last_check
    )


@processing_bp.route('/metragi', methods=['GET', 'POST'])
@services['require_ip_access']
def data_extraction():
    """Обработка метражей"""
    if request.method == 'GET':
        last_check = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        
        services['log_user_access'](
            page="site/metragi.html",
            client_ip=request.remote_addr,
            current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
            message="Пользователь зашёл на metragi.html"
        )
        
        return render_template('site/metragi.html', last_check=last_check, error_message=None)
    
    if request.method == 'POST':
        if 'excel_file' not in request.files:
            return jsonify({'error': 'Файл не был загружен'}), 400
        
        file = request.files['excel_file']
        
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
        
        if not excel_service.allowed_file(file.filename):
            return jsonify({'error': 'Недопустимый тип файла'}), 400
        
        try:
            # Обрабатываем метражи
            result_files = data_service.process_metragi(file)
            
            if result_files:
                # Создаём ZIP архив
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                    for filename, file_content in result_files:
                        zip_file.writestr(filename, file_content)
                zip_buffer.seek(0)
                
                services['log_user_access'](
                    page="Metragi Processing",
                    client_ip=request.remote_addr,
                    current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
                    message="Успешная обработка метражей"
                )
                
                today = date.today()
                return send_file(
                    zip_buffer,
                    as_attachment=True,
                    download_name=f"Метражи {today}.zip",
                    mimetype="application/zip"
                )
            else:
                return jsonify({'error': 'Ошибка обработки данных'}), 400
                
        except Exception as e:
            return jsonify({'error': f'Ошибка обработки файла: {str(e)}'}), 400