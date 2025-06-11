# web/templates/Nexus/autolost/logic/lost_contracts_logic.py
"""
Бизнес-логика для обработки потерянных договоров
"""

import polars as pl
from pathlib import Path
import os
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import traceback
import requests


def process_lost_contracts(contracts_path, progress_callback=None, status_callback=None, check_cancelled=None):
    """
    Обработка файла потерянных договоров
    
    Args:
        contracts_path: Путь к файлу договоров
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
            
        # Шаг 1: Чтение файла
        current_step += 1
        current_status = "Чтение файла..."
        emit_status(current_status)
        emit_progress(int((current_step / total_steps) * 100))
        
        if is_cancelled():
            return None
        
        print(f"Читаем файл: {contracts_path}")
        
        try:
            main_df = pl.read_excel(contracts_path, infer_schema_length=0)
            print(f"Основной DataFrame shape: {main_df.shape}")
            print(f"Колонки: {main_df.columns}")
        except Exception as e:
            raise Exception(f"Ошибка чтения файла договоров: {e}")
        
        # Проверяем наличие необходимых колонок
        required_columns = ["Id", "Номер договора", "Вид страхования", "Физ. лицо.Id записи в DWH"]
        missing_columns = [col for col in required_columns if col not in main_df.columns]
        if missing_columns:
            print(f"Доступные колонки: {main_df.columns}")
            raise Exception(f"В файле отсутствуют колонки: {missing_columns}")
        
        main_df = main_df.select(required_columns)
        print(f"После выбора колонок shape: {main_df.shape}")
        
        if is_cancelled():
            return None
        
        # Шаг 2: Подключение к PostgreSQL
        current_step += 1
        current_status = "Подключение к PostgreSQL..."
        emit_status(current_status)
        emit_progress(int((current_step / total_steps) * 100))
        
        # Подготавливаем параметры для запроса
        server_url = "http://192.168.50.220:5000/sql/query"
        start_date = (date.today().replace(day=1) - relativedelta(months=2)).strftime("%Y-%m-%d")
        end_date = (date.today().replace(day=1) + relativedelta(months=3) - relativedelta(days=1)).strftime("%Y-%m-%d")
        
        # Получаем уникальные MDM ID
        mdm_values = main_df["Физ. лицо.Id записи в DWH"].drop_nulls().unique().to_list()
        if not mdm_values:
            raise Exception("Нет MDM ID для запроса к базе данных")
        
        print(f"Найдено {len(mdm_values)} уникальных MDM ID")
        print(f"Период: {start_date} - {end_date}")
        
        # Формируем SQL запрос
        query = f"""WITH params AS (
    SELECT
    '{start_date}'::DATE AS start_date,
    '{end_date}'::DATE AS end_date,
    ARRAY[{', '.join(map(str, mdm_values))}] AS mdm_ids
    ),
    mdm_ids_table AS (
    SELECT unnest(mdm_ids) AS mdm_id -- Разворачиваем массив mdm_ids в отдельные строки
    FROM params
    ),
    date_ranges AS ( -- Добавил CTE для хранения интервала дат
    SELECT start_date, end_date
    FROM params
    )
    SELECT
    t1.mdm_id,
    t2.contract_number,
    t2.vid_char,
    t2.contract_ins_prg_name,
    t2.contract_channel_name,
    t2.variant_branch_name,
    t2.contract_z_date::DATE,
    t2.variant_ins_sum,
    t2.contract_ppr_sum
    FROM mdm_ids_table AS t1
    CROSS JOIN date_ranges  -- Используем CROSS JOIN чтобы сопоставить каждый мдм с диапазоном дат
    LEFT JOIN _ins_contract AS t2
    ON t1.mdm_id = t2.strah_master_id
    AND date_ranges.start_date <= t2.contract_z_date::DATE  -- Используем start_date из CTE date_ranges
    AND date_ranges.end_date >= t2.contract_z_date::DATE   -- Используем end_date  из CTE date_ranges
    AND t2.contract_termination_f = 0
    WHERE
    t2.contract_ins_prg_name IN ('ОСАГО ФЛ', 'КАСКО Классика ФЛ', 'Комплексное ипотечное страхование', 'Медицина без границ')
    ORDER BY
    t1.mdm_id,
    t2.contract_z_date;"""
        
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
        
        # Обрабатываем vid_char
        result_df = result_df.with_columns(
            pl.col("vid_char")
            .str.replace("0", "Обязательное страхование АГО ФЛ", literal=True)
            .str.replace("И", "Имущество граждан", literal=True)
            .str.replace("U", "Имущество граждан", literal=True)
            .str.replace("П", "Страхование граждан от несчастных случаев и болезней", literal=True)
            .alias("vid_char")
        )
        
        # Фильтруем только нужные виды страхования
        valid_insurance_types = [
            "Обязательное страхование АГО ФЛ", 
            "Имущество граждан", 
            "Страхование граждан от несчастных случаев и болезней"
        ]
        result_df = result_df.filter(pl.col("vid_char").is_in(valid_insurance_types))
        
        # Выбираем нужные колонки
        result_df = result_df.select([
            "mdm_id", "contract_number", "vid_char", 
            "contract_z_date", "contract_ppr_sum"
        ])
        
        print(f"После обработки PostgreSQL данных shape: {result_df.shape}")
        
        # Объединяем с основными данными
        main_df = main_df.join(
            result_df, 
            left_on="Физ. лицо.Id записи в DWH", 
            right_on="mdm_id", 
            how="inner"
        )
        
        print(f"После join shape: {main_df.shape}")
        
        # Фильтруем по совпадению видов страхования
        main_df = main_df.filter(pl.col("Вид страхования") == pl.col("vid_char"))
        
        print(f"После фильтрации по виду страхования shape: {main_df.shape}")
        
        # Выбираем финальные колонки
        main_df = main_df.select([
            "Id", "Номер договора", "contract_number", 
            "contract_z_date", "contract_ppr_sum"
        ])
        
        # Обрабатываем дату
        main_df = main_df.with_columns(
            pl.col("contract_z_date")
            .str.strptime(pl.Date, "%a, %d %b %Y %H:%M:%S GMT", strict=False)
            .dt.strftime("%d.%m.%Y")
            .alias("contract_z_date")
        )
        
        # Переименовываем колонки
        main_df = main_df.rename({
            "contract_number": "Следующий договор", 
            "contract_z_date": "Дата Фронт", 
            "contract_ppr_sum": "Сумма фронт"
        })
        
        # Добавляем статус
        main_df = main_df.with_columns(pl.lit("Действующий").alias("Статус Фронт"))
        
        # Форматируем сумму
        main_df = main_df.with_columns(
            pl.col("Сумма фронт").cast(pl.Float64).map_elements(
                lambda x: f"{x:.2f}".replace(".", ",") if x is not None else None, 
                return_dtype=pl.Utf8
            ).alias("Сумма фронт")
        )
        
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
        output_file = results_dir / f"Потеряшки {current_date}.xlsx"
        
        print(f"Сохраняем результат в: {output_file}")
        print(f"Итоговый DataFrame shape: {main_df.shape}")
        
        main_df.write_excel(output_file)
        
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