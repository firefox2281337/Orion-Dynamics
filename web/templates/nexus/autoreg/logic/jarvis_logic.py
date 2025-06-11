# web/templates/nexus/autojarvis/logic/jarvis_logic.py
"""
Бизнес-логика для обработки Джарвиса
"""

import polars as pl
import pandas as pd
from pathlib import Path
import os
from datetime import datetime
import traceback
import requests
import json
import pyodbc
import re


def process_jarvis_files(prodagi_files, neprol_file, employ_file, 
                        progress_callback=None, status_callback=None, check_cancelled=None):
    """
    Обработка файлов Джарвиса
    
    Args:
        prodagi_files: Список путей к файлам продаж
        neprol_file: Путь к файлу не пролонгированных
        employ_file: Путь к файлу сотрудников
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
    
    # Заголовки для Джарвиса
    headers_js = [
        "№ договора страхования", "Договор страхования, Дата заключения", "Договор страхования, Дата начала", 
        "Договор страхования, Дата окончания", "срок страхования, мес.", "Продукт", "Банк - Выгодоприобретатель", 
        "Страхователь", "Номер телефона", "Объект страхования", "Премия (руб.)", "Страхуется имущество по ипотеке в ВСК", 
        "Объект является новостройкой", "Дата сдачи", "Состояние", "Точка продаж", "Кто ввел", 
        "Кто оформил", "% КВ базовое агента Банка-выгодоприобретателя", "% КВ базовое основного агента", 
        "% КВ по договору общее", "Скидка за счет КВ основного агента", "Итоговое КВ по договору", 
        "Итоговый тарифНсиБ Застрахованный 1", "Итоговый тарифНсиБ Застрахованный 2", "Итоговый тарифНсиБ Застрахованный 3", 
        "Итоговый тарифКонструктивные элементы", "Итоговый тарифТитул", "Коэффициент за суммарный КВ на договоре", 
        "Повышающий коэффициент", "Рассчитанный коэффициент", "Андеррайтерский коэффициент по договору", 
        "Андеррайтерский коэффициент по жизни Застрахованного 1", "Андеррайтерский коэффициент по жизни Застрахованного 2", 
        "Андеррайтерский коэффициент по жизни Застрахованного 3", "Андеррайтерский коэффициент по Имуществу", 
        "Андеррайтерский коэффициент по Титулу", "Понижающий коэф. по НСиБ", "Понижающий коэф. Имущество", 
        "Понижающий коэф. Титул", "№ АгД", "Филиал", "ФИО/ Наименование агента 2", "Логин агента из WEB", 
        "Номер предыдущего договора", "Канал продаж", "Табельный номер агента", "Статус оплаты", 
        "Страховой период", "Дата последнего платежа"
    ]
    
    def clean_columns(df):
        """Очистка названий колонок"""
        df.columns = [re.sub(r'\W+', '_', col).strip() for col in df.columns]
        df = df.select([col for col in df.columns if "__UNNAMED__" not in col and col.strip() != ""])
        return df
    
    def cast_to_str(df):
        """Приведение всех колонок к строковому типу"""
        for col in df.columns:
            df = df.with_columns(df[col].cast(pl.Utf8).alias(col))
        return df
    
    def load_data(file_path):
        """Загрузка данных из файла продаж"""
        df = pd.read_excel(file_path, engine="xlrd")
        df = df.iloc[3:, 1:]  # Пропускаем первые 3 строки и первый столбец
        df = df.astype(str)
        df = pl.from_pandas(df)
        df = df.rename({old: new for old, new in zip(df.columns, headers_js)})
        df = clean_columns(df)
        df = cast_to_str(df)
        return df
    
    try:
        total_steps = 10
        current_step = 0
        current_status = None
        
        emit_status("Ожидание...")
        if is_cancelled():
            return None
        
        # Путь к файлу Джарвиса (теперь parquet)
        jarvis_path = Path(r"D:\server_database\jarvis\Джарвис.parquet")
        
        # Шаг 1: Обновление Джарвис.parquet
        current_step += 1
        current_status = "Обновление Джарвис.parquet..."
        emit_status(current_status)
        emit_progress(int((current_step / total_steps) * 100))
        
        if is_cancelled():
            return None
        
        # Читаем существующий файл Джарвиса
        if jarvis_path.exists():
            try:
                df_jarvis = pl.read_parquet(jarvis_path)
            except Exception as e:
                # Создаем пустой DataFrame с правильными колонками
                df_jarvis = pl.DataFrame({col: [] for col in headers_js})
        else:
            df_jarvis = pl.DataFrame({col: [] for col in headers_js})
        
        df_jarvis = clean_columns(df_jarvis)
        df_jarvis = cast_to_str(df_jarvis)
        
        # Загружаем данные из файлов продаж
        df_list = []
        for prodagi_file in prodagi_files:
            try:
                df = load_data(prodagi_file)
                df_list.append(df)
            except Exception as e:
                raise ConnectionError(f"Ошибка обновления Джарвис: {e}. Ошибка загрузки данных")
        
        # Объединяем все данные
        df_combined = df_jarvis
        for df in df_list:
            df_combined = df_combined.vstack(df)
        
        # Убираем дубликаты
        df_combined = df_combined.unique(subset=["_договора_страхования", "Номер_предыдущего_договора"])
        df_jarvis = df_combined
        
        # Переименовываем обратно к исходным заголовкам
        df_combined = df_combined.rename(dict(zip(df_combined.columns, headers_js)))
    
        
        if is_cancelled():
            return None
        
        # Шаг 2-9: Остальная обработка (упрощенная версия)
        for step in range(2, 10):
            current_step += 1
            current_status = f"Обработка шаг {step}..."
            emit_status(current_status)
            emit_progress(int((current_step / total_steps) * 100))
            
            if is_cancelled():
                return None
        
        # Выбираем нужные колонки для дальнейшей работы
        columns_needed = ["_договора_страхования", "Договор_страхования_Дата_заключения", 
                         "Премия_руб_", "Кто_ввел", "Номер_предыдущего_договора"]
        df_jarvis = df_jarvis.select(columns_needed)
        
        # Читаем файл не пролонгированных
        df = pl.read_excel(neprol_file, infer_schema_length=0)
        df = df.select(["Id", "Номер договора"])
        df = df.with_columns([df[col].cast(pl.Utf8) for col in df.columns])
        
        # Объединяем с данными Джарвиса
        df_jarvis = df_jarvis.with_columns([df_jarvis[col].cast(pl.Utf8) for col in df_jarvis.columns])
        df = df.join(df_jarvis, left_on="Номер договора", right_on="Номер_предыдущего_договора", how="inner")
        df = df.select(["Id", "Номер договора", "_договора_страхования", 
                       "Договор_страхования_Дата_заключения", "Премия_руб_", "Кто_ввел"])
        
        # Подключение к квитовкам (упрощенная версия)
        try:
            conn_str = ("DRIVER={SQL Server};"
                       "SERVER=axcdbrep1\\cdbrep1;"
                       "DATABASE=dstrah;"
                       "Trusted_Connection=yes;")
            batch_size=100
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()
            
            # Получаем данные из квитовок
            search_values_list = df[:, 2].drop_nulls().to_list()
            results = []
            
            for i in range(0, len(search_values_list), batch_size):
                batch = search_values_list[i:i + batch_size]
                batch_str = ",".join(f"''{val}''" for val in batch)
                
                sql_query = f"""
                SELECT CF_ITEM_DOCUMENT, CF_ITEM_AMOUNT 
                FROM OPENQUERY(
                    [adinsure_prod],
                    'SELECT e.CF_ITEM_DOCUMENT, e.CF_ITEM_AMOUNT 
                    FROM ADINSURE_VSK.VSK_ETL_REPORT_NOBD e 
                    LEFT JOIN adinsure_vsk.cf_group_payment_item gpi 
                        ON gpi.GROUP_PAYMENT_ITEM_ID = e.CF_GROUP_PAYMENT_ITEM_ID 
                    LEFT JOIN adinsure_vsk.CT_BC_BILLING_DOC_ITEM_STATUS bis 
                        ON bis.BILLING_DOC_ITEM_STATUS_ID = gpi.STATUS 
                    WHERE e.CF_ITEM_DOCUMENT IN ({batch_str})')"""
                try:
                    cursor.execute(sql_query)
                    batch_results = cursor.fetchall()
                    if batch_results:
                        results.extend(batch_results)
                except pyodbc.Error as e:
                    continue
            
            # Добавляем данные квитовок
            if results:
                results_df = pl.DataFrame({
                    'CF_ITEM_DOCUMENT': [r[0] for r in results],
                    'CF_ITEM_AMOUNT': [r[1] for r in results]
                })
                results_df = results_df.unique()
                df = df.join(results_df, left_on='_договора_страхования', 
                           right_on='CF_ITEM_DOCUMENT', how='left')
            else:
                df = df.with_columns([
                    pl.lit(None).alias('CF_ITEM_AMOUNT')
                ])
                
        except Exception as e:
            df = df.with_columns([
                pl.lit(None).alias('CF_ITEM_AMOUNT')
            ])
        
        conn.close()

        try:
            chunk_size = 990
            server_url = "http://192.168.50.220:5000/sql/query"
            query_values = df["_договора_страхования"].drop_nulls().unique().to_list()
            df_results_all = pl.DataFrame()

            for i in range(0, len(query_values), chunk_size):
                chunk = query_values[i:i + chunk_size]
                current_step += 1
                
                current_status = f"Отправка запроса по части {i // chunk_size + 1}/{(len(query_values) + chunk_size - 1) // chunk_size}..."
                emit_status(current_status)
                emit_progress(int((current_step / total_steps) * 100))
                
                if is_cancelled():
                    return None
                    
                query_str = ", ".join(f"'{val}'" for val in chunk)
                sql_query = f"""
                    SELECT DOG, PAY_DATE
                    FROM ADINSURE_VSK.VSK_DOG_VISTAVLSCHETA
                    WHERE DOG IN ({query_str})
                """
                request_body = json.dumps({"query": sql_query, "database": "Oracle"})
                
                try:
                    response = requests.post(server_url, headers={"Content-Type": "application/json"}, 
                                           data=request_body, timeout=30)
                    response.raise_for_status()
                    
                    data = response.json()
                    columns = data.get("columns", [])
                    rows = data.get("rows", [])

                    if rows:
                        df_results_chunk = pl.DataFrame(rows, schema=columns)
                        df_results_chunk = df_results_chunk.unique()
                        df_results_all = pl.concat([df_results_all, df_results_chunk], how="vertical")
                        print(f"Получено данных из Oracle: {df_results_chunk.shape}")
                        
                except requests.exceptions.RequestException as e:
                    print(f"Ошибка запроса к Oracle: {e}")
                    continue
                except Exception as e:
                    print(f"Ошибка обработки ответа Oracle: {e}")
                    continue

            # Объединяем полученные данные с основным DataFrame
            if df_results_all.height > 0:
                df_results_all = df_results_all.unique()
                print(f"Всего данных из Oracle: {df_results_all.shape}")
                df = df.join(df_results_all, left_on='_договора_страхования', right_on='DOG', how='left')
                print(f"После join с Oracle: {df.shape}")
            else:
                print("Нет данных из Oracle, добавляем пустую колонку")
                df = df.with_columns([pl.lit(None).alias('PAY_DATE')])
                
        except Exception as e:
            print(f"Ошибка подключения к Oracle: {e}")
            df = df.with_columns([pl.lit(None).alias('PAY_DATE')])
        
        # Определяем статус
        print("Определяем статус...")
        print(f"Колонки в DataFrame: {df.columns}")
        
        # Проверяем наличие нужных колонок перед созданием статуса
        cf_amount_exists = "CF_ITEM_AMOUNT" in df.columns
        pay_date_exists = "PAY_DATE" in df.columns
        
        if cf_amount_exists and pay_date_exists:
            df = df.with_columns(
                pl.when(pl.col("CF_ITEM_AMOUNT").is_not_null() | pl.col("PAY_DATE").is_not_null())
                .then(pl.lit("Действующий"))
                .otherwise(pl.lit(""))
                .alias("Статус Фронт")
            )
        elif cf_amount_exists:
            df = df.with_columns(
                pl.when(pl.col("CF_ITEM_AMOUNT").is_not_null())
                .then(pl.lit("Действующий"))
                .otherwise(pl.lit(""))
                .alias("Статус Фронт")
            )
        elif pay_date_exists:
            df = df.with_columns(
                pl.when(pl.col("PAY_DATE").is_not_null())
                .then(pl.lit("Действующий"))
                .otherwise(pl.lit(""))
                .alias("Статус Фронт")
            )
        else:
            print("Нет данных для определения статуса, добавляем пустой статус")
            df = df.with_columns([pl.lit("").alias("Статус Фронт")])
        
        if is_cancelled():
            return None
        
        # Финальные исправления
        if employ_file:
            try:
                df_employee = pl.read_excel(employ_file, infer_schema_length=0)
                columns_needed = ["ФИО", "Физ. лицо.Id"]
                if all(col in df_employee.columns for col in columns_needed):
                    df_employee = df_employee.select(columns_needed)
                    df = df.join(df_employee, left_on='Кто_ввел', right_on='ФИО', how='left')
                else:
                    df = df.with_columns([pl.lit(None).alias('Физ. лицо.Id')])
            except Exception as e:
                print(f"Ошибка обработки файла сотрудников: {e}")
                df = df.with_columns([pl.lit(None).alias('Физ. лицо.Id')])
        else:
            df = df.with_columns([pl.lit(None).alias('Физ. лицо.Id')])
        
        # Убираем лишние колонки
        columns_to_drop = ["CF_ITEM_AMOUNT", "PAY_DATE", "Кто_ввел"]
        for col in columns_to_drop:
            if col in df.columns:
                df = df.drop(col)
        
        # Переименовываем колонки
        new_columns = ["Id", "Номер договора", "Следующий договор", "Дата Фронт", 
                      "Сумма Фронт", "Статус Фронт", "Куратор по договору.Id"]
        
        # Убеждаемся что у нас правильное количество колонок
        current_columns = df.columns
        if len(current_columns) >= len(new_columns):
            # Переименовываем первые колонки
            rename_mapping = {current_columns[i]: new_columns[i] 
                            for i in range(min(len(current_columns), len(new_columns)))}
            df = df.rename(rename_mapping)
            
            # Убираем лишние колонки если есть
            df = df.select(new_columns[:len(current_columns)])
        
        # Переупорядочиваем колонки
        final_columns = ["Id", "Номер договора", "Следующий договор", "Сумма Фронт", 
                        "Дата Фронт", "Статус Фронт", "Куратор по договору.Id"]
        available_columns = [col for col in final_columns if col in df.columns]
        df = df.select(available_columns)
        
        # Убираем дубликаты
        df = df.unique(subset=["Id"])
        
        # Форматируем сумму
        if "Сумма Фронт" in df.columns:
            df = df.with_columns(pl.col("Сумма Фронт").str.replace_all("\\.", ","))
        
        print(f"Финальный DataFrame shape: {df.shape}")
        
        if is_cancelled():
            return None
        
        # Шаг 10: Сохранение
        current_step += 1
        current_status = "Сохранение..."
        emit_status(current_status)
        emit_progress(int((current_step / total_steps) * 100))
        
        # Сохраняем результат
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)
        
        current_date = datetime.now().strftime("%d.%m.%Y")
        output_file = results_dir / f"Джарвис {current_date}.xlsx"
        
        df.write_excel(output_file)
        
        # Сохраняем обновленный файл Джарвиса
        try:
            jarvis_path.parent.mkdir(parents=True, exist_ok=True)
            df_combined.write_parquet(jarvis_path)
            print(f"Обновлен файл Джарвиса: {jarvis_path}")
        except Exception as e:
            print(f"Ошибка сохранения файла Джарвиса: {e}")
        
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