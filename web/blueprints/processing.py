# web/blueprints/processing.py
"""
Сервис для управления задачами обработки
"""

import sys
import importlib
import threading
import traceback
from pathlib import Path


class ProcessingTask:
    """Класс для управления задачей обработки"""
    
    def __init__(self):
        self.is_running = False
        self.progress = 0
        self.status = "Ожидание..."
        self.error = None
        self.result_file = None
        self.cancelled = False

    def reset(self):
        """Сброс состояния задачи"""
        self.is_running = False
        self.progress = 0
        self.status = "Ожидание..."
        self.error = None
        self.result_file = None
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


class ProcessingService:
    """Сервис для обработки файлов"""
    
    BUSINESS_LOGIC_MODULE = "web.templates.nexus.autoreg.logic.business_logic"
    
    def __init__(self):
        self.current_task = ProcessingTask()
    
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
    
    def process_files(self, verint_file, call_file):
        """
        Запуск обработки файлов в отдельном потоке
        
        Args:
            verint_file: Файл Verint
            call_file: Файл Call
            
        Returns:
            bool: True если обработка запущена успешно
        """
        if self.current_task.is_running:
            return False, "Обработка уже выполняется"
        
        # Сохраняем файлы временно
        temp_dir = Path(r"C:\Users\EPopkov\Documents\Orion Dynamics\temp_uploads")
        temp_dir.mkdir(exist_ok=True)
        
        verint_path = temp_dir / verint_file.filename
        call_path = temp_dir / call_file.filename
        
        verint_file.save(verint_path)
        call_file.save(call_path)
        
        # Запускаем обработку в отдельном потоке
        self.current_task.reset()
        self.current_task.is_running = True
        
        thread = threading.Thread(
            target=self._run_processing,
            args=(verint_path, call_path)
        )
        thread.daemon = True
        thread.start()
        
        return True, "Обработка начата"
    
    def _run_processing(self, verint_path, call_path):
        """Внутренний метод для выполнения обработки"""
        try:
            # Перезагружаем бизнес-логику перед выполнением
            if not self.reload_business_logic():
                self.current_task.error = "Ошибка перезагрузки модуля"
                self.current_task.is_running = False
                return
            
            # Импортируем обновленный модуль
            business_logic = sys.modules[self.BUSINESS_LOGIC_MODULE]
            
            # Запускаем обработку
            result_file = business_logic.process_files(
                verint_path, 
                call_path, 
                progress_callback=self.current_task.update_progress,
                status_callback=self.current_task.update_status,
                check_cancelled=lambda: self.current_task.cancelled
            )
            
            self.current_task.result_file = result_file
            self.current_task.status = "Успешно выполнено!"
            self.current_task.progress = 100
            
        except Exception as e:
            self.current_task.error = str(e)
            self.current_task.status = f"Ошибка: {str(e)}"
            print(traceback.format_exc())
        finally:
            self.current_task.is_running = False
            # Очищаем временные файлы
            try:
                verint_path.unlink(missing_ok=True)
                call_path.unlink(missing_ok=True)
            except:
                pass
    
    def get_status(self):
        """Получение текущего статуса обработки"""
        return {
            'is_running': self.current_task.is_running,
            'progress': self.current_task.progress,
            'status': self.current_task.status,
            'error': self.current_task.error,
            'has_result': self.current_task.result_file is not None
        }
    
    def cancel_processing(self):
        """Отмена текущей обработки"""
        self.current_task.cancel()
        return {'message': 'Обработка отменена'}
    
    def get_result_file(self):
        """Получение файла результата"""
        return self.current_task.result_file