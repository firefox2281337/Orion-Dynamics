"""
Бизнес-логика для обработки реестра сделок
"""

import polars as pl
from pathlib import Path
import os
from datetime import datetime
import traceback


def process_registry_files(deals_path, check_path, employee_path, 
                          progress_callback=None, status_callback=None, check_cancelled=None):
    """
    Обработка файлов реестра сделок
    
    Args:
        deals_path: Путь к файлу сделок
        check_path: Путь к файлу проверки 
        employee_path: Путь к файлу сотрудников
        progress_callback: Функция для обновления прогреса
        status_callback: Функция для обновления статуса
        check_cancelled: Функция для проверки отмены
    
    Returns:
        Путь к файлу результата
    """
    
    def emit_progress(value):
        if progress_callback:
            progress_callback(value)
    
    def emit_status(status):
        if status_callback:
            status_callback(status)
    
    def is_cancelled():
        return check_cancelled() if check_cancelled else False
    
    try:
        total_steps = 4
        current_step = 0
        current_status = None
        
        emit_status("Ожидание...")
        if is_cancelled():
            return None
            
        # Шаг 1: Открытие книг
        current_step += 1
        current_status = "Открытие книг..."
        emit_status(current_status)
        emit_progress(int((current_step / total_steps) * 100))
        
        if is_cancelled():
            return None
        
        # Читаем файлы
        employee_df = pl.read_excel(employee_path, infer_schema_length=0)
        check_deals_df = pl.read_excel(check_path, infer_schema_length=0)
        deals_df = pl.read_excel(deals_path, infer_schema_length=0)
        
        if is_cancelled():
            return None
        
        # Шаг 2: Перенос данных по проекту договора
        current_step += 1
        current_status = "Перенос данных по проекту договора..."
        emit_status(current_status)
        emit_progress(int((current_step / total_steps) * 100))
        
        # Обработка данных проверки сделок
        check_deals_df = check_deals_df.select([
            "Проект договора", 
            "Ответственный за лид.Сотрудник.Руководитель.Отдел", 
            "Физ.лицо.Id"
        ])
        check_deals_df = check_deals_df.unique()
        
        # Объединяем с основными сделками
        deals_df = deals_df.join(
            check_deals_df, 
            left_on="Номер договора", 
            right_on="Проект договора", 
            how="left"
        )
        
        # Приводим названия отделов к стандартному виду
        deals_df = deals_df.with_columns(
            pl.col("Ответственный за лид.Сотрудник.Руководитель.Отдел")
            .str.replace("Дирекция пролонгации Ипотеки", "Ипотека", literal=True)
            .str.replace("Центр обслуживания клиентов Волгоград (ЦОК)", "Филиал Волгоград", literal=True)
            .str.replace("Пролонгация КАСКО (Дирекция моторы)", "КАСКО", literal=True)
            .str.replace("VIP-менеджеры", "VIP", literal=True)
            .str.replace("VIP Московский филиал", "VIP", literal=True)
            .str.replace("Группа продаж Ипотека", "УДП", literal=True)
            .str.replace("Группа продаж чаты", "УДП", literal=True)
            .str.replace("Сотрудники CRM", "УДП", literal=True)
            .str.replace("Активный контакт-центр (АКЦ)", "УДП", literal=True)
            .str.replace("Группа продаж ОСАГО", "УДП", literal=True)
            .str.replace("Группа продаж КАСКО", "УДП", literal=True)
            .str.replace("Группа продаж", "УДП", literal=True)
            .alias("Ответственный за лид.Сотрудник.Руководитель.Отдел")
        )
        
        # Фильтруем только нужные подразделения
        valid_values = ["Ипотека", "КАСКО", "ОСАГО", "УДП", "Филиал Волгоград", "VIP"]
        deals_df = deals_df.filter(
            pl.col("Ответственный за лид.Сотрудник.Руководитель.Отдел").is_in(valid_values) | 
            pl.col("Ответственный за лид.Сотрудник.Руководитель.Отдел").is_null()
        )
        
        if is_cancelled():
            return None
        
        # Шаг 3: Перенос данных из джарвиса
        current_step += 1
        current_status = "Перенос данных из джарвиса..."
        emit_status(current_status)
        emit_progress(int((current_step / total_steps) * 100))
        
        # Читаем данные из Джарвиса (если файл существует)
        jarvis_path = Path(r"D:\server_database\jarvis\Джарвис.parquet")
        
        if jarvis_path.exists():
            try:
                jarvis_df = pl.read_parquet(jarvis_path)
                
                # Проверяем наличие необходимых колонок
                required_jarvis_columns = ["№ договора страхования", "Кто ввел"]
                missing_jarvis_columns = [col for col in required_jarvis_columns if col not in jarvis_df.columns]
                
                if missing_jarvis_columns:
                    deals_df = deals_df.with_columns(pl.lit(None).alias("Кто ввел"))
                else:
                    jarvis_df = jarvis_df.select(required_jarvis_columns)
                    
                    deals_df = deals_df.join(jarvis_df, left_on="Номер договора", right_on="№ договора страхования", how="left")
                    
            except Exception as e:
                deals_df = deals_df.with_columns(pl.lit(None).alias("Кто ввел"))
        else:
            deals_df = deals_df.with_columns(pl.lit(None).alias("Кто ввел"))
        
        # Обрабатываем данные о сотрудниках
        employee_df = employee_df.select(["Id", "Физ. лицо"])
        deals_df = deals_df.join(
            employee_df, 
            left_on="Кто ввел", 
            right_on="Физ. лицо", 
            how="left"
        )
        
        # Очищаем и переименовываем колонки
        deals_df = deals_df.drop("Кто ввел")
        deals_df = deals_df.rename({
            "Ответственный за лид.Сотрудник.Руководитель.Отдел": "Ответственное подразделение",
            "Id": "Куратор по договору.id"
        })
        
        # Убираем дубликаты
        deals_df = deals_df.unique(subset=["Номер договора"])
        
        if is_cancelled():
            return None
        
        # Шаг 4: Сохранение
        current_step += 1
        current_status = "Сохранение..."
        emit_status(current_status)
        emit_progress(int((current_step / total_steps) * 100))
        
        # Сохраняем в папку results
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)
        
        current_date = datetime.now().strftime("%d.%m.%Y")
        output_file = results_dir / f"Сделки {current_date}.xlsx"
        
        deals_df.write_excel(output_file)
        
        emit_status("Успешно выполнено!")
        emit_progress(100)
        
        return str(output_file)
        
    except Exception as e:
        error_message = f"Ошибка на шаге: {current_status}\n{traceback.format_exc()}"
        emit_status(error_message)
        
        # Сохраняем лог ошибки
        try:
            results_dir = Path("results")
            results_dir.mkdir(exist_ok=True)
            error_file_path = results_dir / "error_log.txt"
            
            with open(error_file_path, "a", encoding="utf-8") as error_file:
                error_file.write(f"{datetime.now()}: {error_message}\n")
        except:
            pass
        
        raise e