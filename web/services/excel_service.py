# web/services/excel_service.py
"""
Сервис для работы с Excel файлами
"""

import os
import io
import pandas as pd
from werkzeug.utils import secure_filename
from core.config.db_config import ALLOWED_EXTENSIONS


class ExcelService:
    """Сервис для работы с Excel файлами"""
    
    def __init__(self, upload_folder="temp_uploads"):
        self.upload_folder = upload_folder
        os.makedirs(upload_folder, exist_ok=True)
    
    def allowed_file(self, filename):
        """Проверка разрешённого расширения файла"""
        return ('.' in filename and 
                filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS)
    
    def upload_and_read_headers(self, file):
        """
        Загружает Excel файл и возвращает заголовки
        
        Args:
            file: Файл из request.files
            
        Returns:
            dict: Словарь с заголовками или ошибкой
        """
        if not file or file.filename == '':
            return {'error': 'Файл не выбран'}
        
        if not self.allowed_file(file.filename):
            return {'error': 'Недопустимый тип файла'}
        
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(self.upload_folder, filename)
            file.save(filepath)
            
            # Читаем только заголовки
            df = pd.read_excel(filepath, nrows=0)
            headers = df.columns.tolist()
            
            # Удаляем временный файл
            os.remove(filepath)
            
            return {'headers': headers}
            
        except Exception as e:
            return {'error': f'Ошибка при обработке файла: {str(e)}'}
    
    def read_excel_file(self, filepath, sheet_name=0, dtype=str):
        """
        Читает Excel файл
        
        Args:
            filepath: Путь к файлу
            sheet_name: Название или номер листа
            dtype: Тип данных для чтения
            
        Returns:
            pandas.DataFrame: DataFrame с данными файла
        """
        try:
            return pd.read_excel(filepath, sheet_name=sheet_name, dtype=dtype)
        except Exception as e:
            raise Exception(f"Ошибка при чтении Excel файла: {str(e)}")
    
    def save_to_excel(self, data, filename="results.xlsx"):
        """
        Сохраняет данные в Excel файл в памяти
        
        Args:
            data: Данные для сохранения (list of lists или DataFrame)
            filename: Имя файла
            
        Returns:
            io.BytesIO: Объект BytesIO с Excel файлом
        """
        try:
            mem = io.BytesIO()
            
            if isinstance(data, list) and len(data) > 1:
                # Если данные в виде списка списков
                headers = data[0]
                data_rows = data[1:]
                df = pd.DataFrame(data_rows, columns=headers)
            elif isinstance(data, pd.DataFrame):
                # Если данные уже в виде DataFrame
                df = data
            else:
                raise ValueError("Неподдерживаемый формат данных")
            
            df.fillna("", inplace=True)
            
            with pd.ExcelWriter(mem, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Sheet1', index=False)
            
            mem.seek(0)
            return mem
            
        except Exception as e:
            raise Exception(f"Ошибка при сохранении Excel файла: {str(e)}")
    
    def generate_report(self, selected_quarter, selected_year, selected_checkboxes, base_path):
        """
        Генерирует отчёт из нескольких Excel файлов
        
        Args:
            selected_quarter: Выбранный квартал
            selected_year: Выбранный год
            selected_checkboxes: Список номеров филиалов
            base_path: Базовый путь к файлам
            
        Returns:
            io.BytesIO: Объект BytesIO с объединённым Excel файлом
        """
        def read_excel_file(i):
            """Читает Excel файл (xlsx или xlsb)"""
            folder_num = f"{i:02d}"
            file_num_xlsx = f"{i:04d}.xlsx"
            file_num_xlsb = f"{i:04d}.xlsb"
            
            folder_path = os.path.join(
                base_path, folder_num, "Автодилеры", "Пролонгация",
                f"{selected_quarter} квартал {selected_year}"
            )
            
            file_path_xlsx = os.path.join(folder_path, file_num_xlsx)
            file_path_xlsb = os.path.join(folder_path, file_num_xlsb)
            
            # Пробуем сначала xlsx
            if os.path.exists(file_path_xlsx):
                try:
                    return pd.read_excel(file_path_xlsx, sheet_name=0, dtype=str)
                except Exception:
                    pass
            
            # Затем xlsb
            if os.path.exists(file_path_xlsb):
                try:
                    return pd.read_excel(file_path_xlsb, sheet_name=0, engine="pyxlsb", dtype=str)
                except Exception:
                    pass
            
            return None
        
        all_data = []
        selected_checkboxes = [int(x) for x in selected_checkboxes]
        
        for i in selected_checkboxes:
            result = read_excel_file(i)
            if result is not None:
                all_data.append(result)
        
        if all_data:
            # Объединяем все колонки
            all_columns = set()
            for df in all_data:
                all_columns.update(df.columns)
            
            # Добавляем недостающие колонки
            for i, df in enumerate(all_data):
                missing_cols = all_columns - set(df.columns)
                missing_df = pd.DataFrame({col: pd.NA for col in missing_cols}, index=df.index)
                all_data[i] = pd.concat([df, missing_df], axis=1)
            
            final_df = pd.concat(all_data, ignore_index=True)
            final_df.fillna("", inplace=True)
        else:
            final_df = pd.DataFrame()
        
        return self.save_to_excel(final_df)