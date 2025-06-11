# web/templates/Nexus/autocampaigns/logic/campaigns_logic.py
"""
Бизнес-логика для проверки кампаний
"""

import polars as pl
from pathlib import Path
import os
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import traceback
import requests


def process_campaigns(cgr_path, progress_callback=None, status_callback=None, check_cancelled=None):
    """
    Обработка файла кампаний
    
    Args:
        cgr_path: Путь к файлу кампаний
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
        total_steps = 5
        current_step = 0
        current_status = None
        
        emit_status("Ожидание...")
        if is_cancelled():
            return None
            
        # Шаг 1: Создание DataFrame
        current_step += 1
        current_status = "Создание DataFrame..."
        emit_status(current_status)
        emit_progress(int((current_step / total_steps) * 100))
        
        if is_cancelled():
            return None
        
        print(f"Читаем файл: {cgr_path}")
        
        try:
            cgr_df = pl.read_excel(cgr_path, infer_schema_length=0)
            print(f"CGR DataFrame shape: {cgr_df.shape}")
            print(f"Колонки: {cgr_df.columns}")
        except Exception as e:
            raise Exception(f"Ошибка чтения файла кампаний: {e}")
        
        # Проверяем наличие необходимых колонок
        required_columns = ["Физ.лицо.Id записи в DWH", "Номер договора"]
        missing_columns = [col for col in required_columns if col not in cgr_df.columns]
        if missing_columns:
            print(f"Доступные колонки: {cgr_df.columns}")
            raise Exception(f"В файле отсутствуют колонки: {missing_columns}")
        
        cgr_df = cgr_df.select(required_columns)
        print(f"После выбора колонок shape: {cgr_df.shape}")
        
        if is_cancelled():
            return None
        
        # Шаг 2: Подключение к PostgreSQL
        current_step += 1
        current_status = "Подключение к PostgreSQL..."
        emit_status(current_status)
        emit_progress(int((current_step / total_steps) * 100))
        
        # Подготавливаем параметры для запроса
        server_url = "http://192.168.50.220:5000/sql/query"
        start_date = (date.today().replace(day=1) - relativedelta(months=2)).strftime("%d-%m-%Y")
        end_date = (date.today().replace(day=1) + relativedelta(months=2)).strftime("%d-%m-%Y")
        
        # Получаем уникальные MDM ID
        mdm_values = cgr_df["Физ.лицо.Id записи в DWH"].drop_nulls().unique().to_list()
        if not mdm_values:
            raise Exception("Нет MDM ID для запроса к базе данных")
        
        print(f"Найдено {len(mdm_values)} уникальных MDM ID")
        print(f"Период: {start_date} - {end_date}")
        
        # Формируем VALUES строку для SQL
        mdm_values_str = ",\n".join(f"({mdm_id}, '{start_date}'::DATE, '{end_date}'::DATE)" for mdm_id in mdm_values)
        
        # Формируем SQL запрос
        query = f"""
        SELECT t1.mdm_id, 
            t2.contract_number, 
            t2.vid_char, 
            t2.contract_ins_prg_name, 
            t2.contract_channel_name, 
            t2.variant_branch_name, 
            t2.contract_z_date::DATE, 
            t2.variant_ins_sum, 
            t2.contract_ppr_sum
        FROM (VALUES {mdm_values_str}) AS t1(mdm_id, date_start, date_end)
        LEFT JOIN _ins_contract AS t2 
        ON t1.mdm_id = t2.strah_master_id 
        AND t1.date_start <= t2.contract_z_date::DATE 
        AND t1.date_end >= t2.contract_z_date::DATE 
        AND t2.contract_termination_f = 0 
        WHERE t2.contract_ins_prg_name IN ('ОСАГО ФЛ', 'КАСКО Классика ФЛ', 'Комплексное ипотечное страхование', 'Медицина без границ') 
        ORDER BY t1.mdm_id, t2.contract_z_date;"""
        
        request_body = {"query": query, "database": "PostgreSQL"}
        print("Отправляем запрос к PostgreSQL...")
        
        try:
            response = requests.post(server_url, json=request_body, headers={"Content-Type": "application/json"})
            if response.status_code != 200:
                raise Exception(f"Ошибка запроса к PostgreSQL: {response.status_code} - {response.text}")
            
            data = response.json()
            columns = data.get("columns", [])
            rows = data.get("rows", [])
            
            if not rows:
                raise Exception("PostgreSQL запрос не вернул данных")
            
            print(f"Получено {len(rows)} записей из PostgreSQL")
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ошибка соединения с PostgreSQL: {e}")
        
        if is_cancelled():
            return None
        
        # Шаг 3: Перенос данных
        current_step += 1
        current_status = "Перенос данных..."
        emit_status(current_status)
        emit_progress(int((current_step / total_steps) * 100))
        
        # Создаем DataFrame из результатов PostgreSQL
        result_df = pl.DataFrame(rows, schema={col: pl.Utf8 for col in columns})
        print(f"Result DataFrame shape: {result_df.shape}")
        
        # Обрабатываем дату
        result_df = result_df.with_columns(
            pl.col("contract_z_date")
            .str.strptime(pl.Date, "%a, %d %b %Y %H:%M:%S GMT", strict=False)
            .dt.strftime("%d.%m.%Y")
            .alias("contract_z_date")
        )
        
        # Получаем уникальные записи из cgr_df
        cgr_df = cgr_df.unique()
        
        # Объединяем с исходными данными
        result_df = result_df.join(cgr_df, left_on='mdm_id', right_on='Физ.лицо.Id записи в DWH', how='left')
        
        print(f"После join с CGR: {result_df.shape}")
        
        if is_cancelled():
            return None
        
        # Шаг 4: Установка значений
        current_step += 1
        current_status = "Установка значений..."
        emit_status(current_status)
        emit_progress(int((current_step / total_steps) * 100))
        
        # Фильтруем по номерам договоров (исключаем совпадения)
        result_df = result_df.filter(pl.col("contract_number") != pl.col("Номер договора"))
        result_df = result_df.drop("Номер договора")
        
        print(f"После фильтрации по номерам договоров: {result_df.shape}")
        
        # Фильтруем по каналам продаж
        valid_values = ["WSM", "Интернет продажи", "Клиентский зал", "Интернет-продажи"]
        result_df = result_df.filter(pl.col("contract_channel_name").is_in(valid_values))
        
        print(f"После фильтрации по каналам: {result_df.shape}")
        
        # Убираем ненужные колонки
        result_df = result_df.drop("vid_char", "contract_ins_prg_name", "variant_branch_name")
        
        # Переименовываем колонки
        result_df = result_df.rename({
            "mdm_id": "Физ.лицо.Id записи в DWH", 
            "contract_number": "Номер договора", 
            "contract_channel_name": "Канал продаж", 
            "contract_z_date": "Дата заключения", 
            "variant_ins_sum": "Страховая сумма по договору", 
            "contract_ppr_sum": "Страховая премия по договору"
        })
        
        # Добавляем статус
        result_df = result_df.with_columns([pl.lit("Активный").alias("Статус договора")])
        
        # Функция для проверки номеров договоров
        def check_conditions(value):
            if len(value) == 13:
                suffix = value[-8:][:3]
                if suffix in {"IPE", "IPA", "IPB", "IPD", "IPZ", "IPI"}:
                    return True
            elif len(value) == 18:
                suffix = value[-13:][:3]
                if suffix in {"IPE", "IPA", "IPB", "IPD", "IPZ", "IPI", "MIP"}:
                    return True
            return False
        
        # Применяем проверку и фильтруем
        result_df = result_df.with_columns(
            pl.col("Номер договора").map_elements(check_conditions, return_dtype=pl.Boolean).alias("Result")
        )
        result_df = result_df.filter(pl.col("Result") == True)
        result_df = result_df.drop("Result")
        
        print(f"После проверки номеров договоров: {result_df.shape}")
        
        # Форматируем суммы
        result_df = result_df.with_columns([
            pl.col("Страховая сумма по договору").cast(pl.Float64).map_elements(
                lambda x: f"{x:.2f}".replace(".", ",") if x is not None else None, 
                return_dtype=pl.Utf8
            ).alias("Страховая сумма по договору"),
            pl.col("Страховая премия по договору").cast(pl.Float64).map_elements(
                lambda x: f"{x:.2f}".replace(".", ",") if x is not None else None, 
                return_dtype=pl.Utf8
            ).alias("Страховая премия по договору")
        ])
        
        if is_cancelled():
            return None
        
        # Шаг 5: Сохранение
        current_step += 1
        current_status = "Сохранение..."
        emit_status(current_status)
        emit_progress(int((current_step / total_steps) * 100))
        
        # Сохраняем в папку results
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)
        
        current_date = datetime.now().strftime("%d.%m.%Y")
        output_file = results_dir / f"Проверка кампаний {current_date}.xlsx"
        
        print(f"Сохраняем результат в: {output_file}")
        print(f"Итоговый DataFrame shape: {result_df.shape}")
        
        result_df.write_excel(output_file)
        
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