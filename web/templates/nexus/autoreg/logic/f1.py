# web/templates/nexus/autoreg/handler_kasko.py
"""
Адаптированный обработчик реестров для веб-интерфейса с возможностью скачивания
"""

import os
import concurrent.futures
import polars as pl
import tempfile
import zipfile
import io
from datetime import datetime
from pathlib import Path
import datetime

# Импорты оригинальных функций
from web.templates.nexus.autoreg.logic.handler_stubs import (
    create_df, parse_and_format_date, generate_external_id, calculate_planned_call_date, set_lead_type, set_insurance_group, 
    steps, clear_columns_dog, make_fio, clean_column, format_phone, clean_phone_column, set_type_of_insure, create_person_file, 
    create_contracts_file_kasko_osago, save_to_excel, set_priority_osago, set_product, set_departament, set_links_osago, 
    set_subdivision, final_format_osago, set_region_and_filial_osago_kasko, fix_auto, create_cars, create_short_links, create_contracts_osago_kz_file
)
from web.templates.nexus.autoreg.logic.data_processing import (
    process_data_operations, fetch_pgsql_data, fetch_actuar2_data, process_data_pgsql
)

class RegistryProcessor:
    """Веб-адаптированный процессор реестров"""
    
    def __init__(self, number, file_path, correspondences, template_headers, register_type="f1"):
        self.is_running = True
        self.number = str(number) if number is not None else "0"
        self.file_path = file_path
        self.correspondences = correspondences
        self.template_headers = template_headers
        self.register_type = "f1"
        
        # Готовые заголовки для обработки
        self.ready_headers = [
            "id физ лица", "Тип лида", "Продукт", "Группа продукта", "Вид страхования", "ФИО", "Фамилия", 
            "Имя", "Отчество", "Дата рождения", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", 
            "Филиал ВСК", "Регион", "Другой полис", "Дополнительные сведения"
        ]
        
        # Колбэки для обновления прогресса
        self.progress_callback = None
        self.status_callback = None
        
        # Папка для результатов
        self.temp_dir = tempfile.mkdtemp(prefix=f"autoreg_{self.number}_")
    
    def set_callbacks(self, progress_callback, status_callback):
        """Установка колбэков для обновления прогресса"""
        self.progress_callback = progress_callback
        self.status_callback = status_callback
    
    def emit_progress(self, progress, step):
        """Отправка обновления прогресса"""
        if self.progress_callback:
            self.progress_callback(progress, step)
    
    def emit_status(self, status):
        """Отправка обновления статуса"""
        if self.status_callback:
            self.status_callback(status)
    
    def web_steps(self, current_step, total_steps, message):
        """Веб-адаптированная функция отслеживания шагов"""
        if not self.is_running:
            return current_step
        
        progress = int((current_step / total_steps) * 100)
        self.emit_progress(progress, message)
        return current_step + 1
    
    def save_excel_to_memory(self, dataframes_with_sheets, filename):
        """Сохранение Excel файла в память для последующей отправки"""
        buffer = io.BytesIO()
        
        try:
            import xlsxwriter
            
            # Создаем workbook с буфером вместо файла
            workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})
            header_format = workbook.add_format({'bold': True})
            
            for df, sheet_name in dataframes_with_sheets:
                if df is not None:
                    worksheet = workbook.add_worksheet(sheet_name)
                    column_widths = {}
                    
                    # Записываем заголовки
                    for col_num, column in enumerate(df.columns):
                        worksheet.write(0, col_num, column, header_format)
                        column_widths[col_num] = len(column) + 2
                    
                    # Записываем данные
                    for row_num, row in enumerate(df.rows(), start=1):
                        for col_num, value in enumerate(row):
                            worksheet.write(row_num, col_num, value)
                            
                            # Обновляем ширину колонки
                            value_length = len(str(value)) if value is not None else 0
                            if value_length + 2 > column_widths.get(col_num, 0):
                                column_widths[col_num] = value_length + 2
                    
                    # Устанавливаем ширину колонок
                    for col_num, width in column_widths.items():
                        worksheet.set_column(col_num, col_num, width)
            
            # Закрываем workbook для записи в буфер
            workbook.close()
            
            # Возвращаем содержимое буфера
            buffer.seek(0)
            return buffer.getvalue()
            
        except Exception as e:
            print(f"Ошибка сохранения файла {filename}: {str(e)}")
            return None
    
    def create_download_package(self, base_type, person, processed_data, no_phone_df):
        """Создание ZIP архива для скачивания"""
        try:
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Файл физ. лиц
                person_data = self.save_excel_to_memory([(person, "Физ лица")], "person.xlsx")
                if person_data:
                    zip_file.writestr(f"1 - Физ лица {base_type}.xlsx", person_data)
                
                # Файл лидов
                leads_sheets = [
                    (processed_data, "Осн"),
                    (no_phone_df, f"Нет телефона ({len(no_phone_df)})") if len(no_phone_df) > 0 else None
                ]
                leads_sheets = [item for item in leads_sheets if item is not None]
                
                leads_data = self.save_excel_to_memory(leads_sheets, "leads.xlsx")
                if leads_data:
                    zip_file.writestr(f"3 - Лиды {base_type}.xlsx", leads_data)
            
            zip_buffer.seek(0)
            return zip_buffer.getvalue()
            
        except Exception as e:
            print(f"Ошибка создания ZIP архива: {str(e)}")
            return None
    
    def run(self):
        """Основная функция обработки"""
        try:
            total_steps = 26  # Увеличили на 1 для создания архива
            current_step = 0
            base_type = self.register_type
            
            if not self.is_running:
                return {'success': False, 'error': 'Процесс остановлен'}
            
            # Проверяем существование файла
            if not os.path.exists(self.file_path):
                return {'success': False, 'error': 'Исходный файл не найден'}
            
            # Шаг 1: Объединение данных
            current_step = self.web_steps(current_step, total_steps, "Объединение данных...")
            result_data = create_df(self.file_path, self.ready_headers, self.correspondences)
            
            if result_data is None or len(result_data) == 0:
                return {'success': False, 'error': 'Не удалось создать DataFrame из файла'}
            print("1. Данные объединены")

            # Шаг 2: Создание базовых столбцов
            current_step = self.web_steps(current_step, total_steps, "Создание базовых столбцов...")
            result_data = result_data.rename({"Другой полис": "№ Договора К Пролонгации"})
            result_data = result_data.with_columns([
                generate_external_id(self.number, result_data, base_type)])
            result_data = result_data.with_columns(pl.col('Тип базы')
                                                   .replace({'kasko_akc': '4.3 Pilot 1F ТМ КАСКО', 
                                                                  'kasko_mos': 'Москва_1Factor_КАСКО', 
                                                                  'ipot_akc': '4.3 Pilot 1F ТМ Ипотека', 
                                                                  'ipot_mos': 'Москва_1Factor_Ипотека'})
                                                                  .alias('Кампания'))
            print("2. Базовые столбцы созданы")

            # Шаг 4: Обработка ФИО
            current_step = self.web_steps(current_step, total_steps, "Разбивка/объединение ФИО...")
            result_data = result_data.with_columns(make_fio())
            print("4. ФИО обработано")

            # Шаг 6: Очистка контактных данных
            current_step = self.web_steps(current_step, total_steps, "Очистка номеров и почты от мусора...")
            columns_to_clean = ["Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail"]
            for col in columns_to_clean:
                if col in result_data.columns:
                    result_data = result_data.with_columns(clean_column(pl.col(col)).alias(col))
            print("6. Контактные данные очищены")

            # Шаг 7: Форматирование телефонов
            current_step = self.web_steps(current_step, total_steps, "Корректировка формата номеров телефона...")
            phone_columns = ["Основной телефон", "Телефон 2", "Телефон 3"]
            for col in phone_columns:
                if col in result_data.columns:
                    result_data = result_data.with_columns(format_phone(col))
            print("7. Телефоны отформатированы")

            # Шаг 8: Удаление дублей телефонов
            current_step = self.web_steps(current_step, total_steps, "Удаление дубликатов номера телефона...")
            result_data = clean_phone_column(result_data, "Основной телефон", "Телефон 2")
            result_data = clean_phone_column(result_data, "Основной телефон", "Телефон 3")
            result_data = clean_phone_column(result_data, "Телефон 2", "Телефон 3")
            print("8. Дубли телефонов удалены")
            
            # Шаг 9: Подключение к БД
            current_step = self.web_steps(current_step, total_steps, "Подключение к БД...")
            server_url = "http://192.168.50.220:5000/sql/query"
            contract_numbers = result_data["№ Договора К Пролонгации"].drop_nulls().unique().to_list()
            print("9. Подключение к БД")

            # Шаг 10: Асинхронное выполнение запросов к БД
            current_step = self.web_steps(current_step, total_steps, "Получение данных из БД...")
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_pgsql = executor.submit(fetch_pgsql_data, server_url, contract_numbers)
                data_dict_pgsql = future_pgsql.result()
            print("10. Данные из БД получены")

            # Шаг 11: Обработка данных из БД
            current_step = self.web_steps(current_step, total_steps, "Перенос данных из БД...")
            result_data = process_data_pgsql(result_data, data_dict_pgsql)
            print("11. Данные из БД обработаны")
            
            # Шаг 13: Разделение данных
            current_step = self.web_steps(current_step, total_steps, "Перенос пустых строк на отдельные листы...")
            no_phone_df = result_data.filter(pl.col("Основной телефон").is_null())
            processed_data = result_data.filter(~(pl.col("Основной телефон").is_null()))

            current_step = self.web_steps(current_step, total_steps, "Обработка филиалов и региона...")
            processed_data = set_region_and_filial_osago_kasko(processed_data)

            current_step = self.web_steps(current_step, total_steps, "Создание файла физ.лиц...")
            person = create_person_file(processed_data)
            processed_data = processed_data.drop("Тип базы")
            processed_data = processed_data.rename({"№ Договора К Пролонгации": "Другой полис", "id физ лица": "Физ лицо.Id записи в dwh"})
            processed_data = processed_data.with_columns(
                pl.when(pl.col("Кампания").is_in(["Москва_1Factor_КАСКО", "Москва_1Factor_Ипотека"]))
                .then(pl.lit(datetime.date.today().replace(day=1)).dt.strftime("%d.%m.%Y"))
                .otherwise(pl.lit(None))
                .alias("Плановая дата звонка CTI")
                )
            print("20. Файл физ.лиц создан")

            # Шаг 25: Создание архива для скачивания
            current_step = self.web_steps(current_step, total_steps, "Создание архива для скачивания...")
            download_data = self.create_download_package(
                base_type, person, processed_data, no_phone_df
            )
            
            if download_data is None:
                return {'success': False, 'error': 'Ошибка создания архива для скачивания'}
            
            # Сохраняем архив во временную папку
            zip_filename = f"{self.number}_{base_type}_пилот.zip"
            zip_path = os.path.join(self.temp_dir, zip_filename)
            
            with open(zip_path, 'wb') as f:
                f.write(download_data)
            
            print("23. Архив для скачивания создан")

            # Шаг 26: Завершение
            current_step = self.web_steps(current_step, total_steps, "Завершение обработки...")
            
            # Завершение
            self.emit_status("Успешно выполнено!")
            self.emit_progress(100, "Завершено")
            
            return {
                'success': True,
                'message': 'Реестр успешно создан',
                'download_file': zip_path,
                'download_filename': zip_filename,
                'temp_dir': self.temp_dir,
                'stats': {
                    'total_records': len(result_data),
                    'processed_records': len(processed_data),
                    'no_phone_records': len(no_phone_df)
                }
            }
            
        except Exception as e:
            self.emit_status(f"Ошибка: {str(e)}")
            self.emit_progress(0, "Ошибка")
            print(f"Ошибка в run(): {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
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