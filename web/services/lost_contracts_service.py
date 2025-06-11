# web/services/lost_contracts_service.py
"""
Сервис для управления задачами обработки потерянных договоров
"""

import sys
import importlib
import threading
import traceback
from pathlib import Path
import re
import uuid


class LostContractsTask:
    """Класс для управления задачей обработки потерянных договоров"""
    
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


class LostContractsService:
    """Сервис для обработки файлов потерянных договоров"""
    
    BUSINESS_LOGIC_MODULE = "web.templates.nexus.autoreg.logic.lost_contracts_logic"
    
    def __init__(self):
        self.current_task = LostContractsTask()
    
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
    
    def safe_filename(self, original_filename):
        """
        Создает безопасное имя файла с сохранением расширения
        """
        # Получаем расширение
        if '.' in original_filename:
            name, ext = original_filename.rsplit('.', 1)
            ext = f".{ext}"
        else:
            name = original_filename
            ext = ""
        
        # Убираем опасные символы
        safe_name = re.sub(r'[<>:"/\\|?*]', '', name)
        safe_name = re.sub(r'\s+', '_', safe_name.strip())
        
        # Если имя пустое после очистки, используем UUID
        if not safe_name:
            safe_name = str(uuid.uuid4())[:8]
        
        return safe_name + ext
    
    def process_file(self, contracts_file):
        """
        Запуск обработки файла в отдельном потоке
        
        Args:
            contracts_file: Файл договоров
            
        Returns:
            tuple: (success, message)
        """
        if self.current_task.is_running:
            return False, "Обработка уже выполняется"
        
        # Сохраняем файл временно
        temp_dir = Path("temp_uploads")
        temp_dir.mkdir(exist_ok=True)
        
        # Создаем безопасное имя файла
        contracts_filename = self.safe_filename(contracts_file.filename)
        contracts_path = temp_dir / contracts_filename
        
        print(f"Сохраняем файл:")
        print(f"  Договора: {contracts_file.filename} -> {contracts_path}")
        
        # Сохраняем файл
        contracts_file.save(contracts_path)
        
        # Запускаем обработку в отдельном потоке
        self.current_task.reset()
        self.current_task.is_running = True
        
        thread = threading.Thread(
            target=self._run_processing,
            args=(contracts_path,)
        )
        thread.daemon = True
        thread.start()
        
        return True, "Обработка начата"
    
    def _run_processing(self, contracts_path):
        """Внутренний метод для выполнения обработки"""
        try:
            print(f"Начинаем обработку файла: {contracts_path}")
            
            # Перезагружаем бизнес-логику перед выполнением
            if not self.reload_business_logic():
                self.current_task.error = "Ошибка перезагрузки модуля"
                self.current_task.is_running = False
                return
            
            # Импортируем обновленный модуль
            business_logic = sys.modules[self.BUSINESS_LOGIC_MODULE]
            
            # Запускаем обработку
            result_file = business_logic.process_lost_contracts(
                contracts_path,
                progress_callback=self.current_task.update_progress,
                status_callback=self.current_task.update_status,
                check_cancelled=lambda: self.current_task.cancelled
            )
            
            self.current_task.result_file = result_file
            self.current_task.status = "Успешно выполнено!"
            self.current_task.progress = 100
            
            print(f"Обработка завершена успешно. Результат: {result_file}")
            
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
                contracts_path.unlink(missing_ok=True)
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
            'has_result': self.current_task.result_file is not None
        }
    
    def cancel_processing(self):
        """Отмена текущей обработки"""
        self.current_task.cancel()
        return {'message': 'Обработка отменена'}
    
    def get_result_file(self):
        """Получение файла результата"""
        return self.current_task.result_file