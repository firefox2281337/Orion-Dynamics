import polars as pl
from pathlib import Path
import os
from datetime import datetime
import traceback

def process_files(verint_path, call_path, progress_callback=None, status_callback=None, check_cancelled=None):
    '''
    Обработка файлов Verint и Call
    
    Args:
        verint_path: Путь к файлу Verint
        call_path: Путь к файлу Call
        progress_callback: Функция для обновления прогресса
        status_callback: Функция для обновления статуса
        check_cancelled: Функция для проверки отмены
    
    Returns:
        Путь к файлу результата
    '''
    
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
        
        emit_status("Ожидание...")
        if is_cancelled():
            return None
            
        # Шаг 1: Создание DataFrame
        current_step += 1
        emit_status("Создание DataFrame...")
        emit_progress(int((current_step / total_steps) * 100))
        
        def load_data(file_path, skip_rows):
            df = pl.read_excel(file_path)
            df = df.slice(skip_rows, df.height - skip_rows)
            return df
        
        anal_df = load_data(verint_path, skip_rows=19)
        anal_df_2 = load_data(verint_path, skip_rows=20)
        call_df = pl.read_excel(call_path)
        
        anal_df = anal_df
        headers = anal_df.row(0)
        headers = [
            col if col and isinstance(col, str) else f"Unnamed_{i}"  
            for i, col in enumerate(headers)
        ]
        
        anal_df_2 = anal_df_2.rename(dict(zip(anal_df_2.columns, headers)))
        anal_df = anal_df_2
        columns = anal_df.columns
        ani_col = next(col for col in columns if "ANI" in col)
        key_col = next(col for col in columns if "E" in col)
        
        start_idx = columns.index(key_col)
        end_idx = columns.index(ani_col)
        selected_columns = columns[start_idx:end_idx]
        
        if is_cancelled():
            return None
        
        # Шаг 2: Поиск категорий
        current_step += 1
        emit_status("Поиск категорий...")
        emit_progress(int((current_step / total_steps) * 100))
        
        def process_row(row):
            result = []
            for col in selected_columns:
                value = row[col]
                if value in [None, ""]:
                    continue
                if isinstance(value, str):
                    try:
                        value = float(value)
                    except ValueError:
                        pass
                if value == "E":
                    result.append("E")
                elif isinstance(value, (int, float)) and 0 <= value <= 1:
                    result.append(col)
            return ";".join(result) + ";"
        
        anal_df = anal_df.with_columns(
            pl.struct(selected_columns).map_elements(process_row).alias("Заметки")
        )
        anal_df = anal_df.select("Идентификатор коммутатора вызова", "Заметки")
        call_df = call_df.select("Id", "Идентификатор звонка")
        call_df = call_df.with_columns(call_df["Идентификатор звонка"].cast(pl.Utf8))
        
        call_df = call_df.join(
            anal_df,
            left_on='Идентификатор звонка', 
            right_on='Идентификатор коммутатора вызова', 
            how='inner'
        )
        
        if is_cancelled():
            return None
        
        # Шаг 3: Очистка лишнего
        current_step += 1
        emit_status("Очистка лишнего...")
        emit_progress(int((current_step / total_steps) * 100))
        
        call_df = call_df.filter(pl.col("Заметки").is_not_null())
        call_df = call_df.unique(subset=["Id"], keep="first")
        call_df = call_df.select("Id", "Заметки")
        call_df = call_df.filter(pl.col("Заметки") != "Uncategorized;")
        
        if is_cancelled():
            return None
        
        # Шаг 4: Сохранение
        current_step += 1
        emit_status("Сохранение...")
        emit_progress(int((current_step / total_steps) * 100))
        
        # Сохраняем в папку results
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)
        
        current_date = datetime.now().strftime("%d.%m.%Y")
        output_file = results_dir / f"Веринт {current_date}.xlsx"
        call_df.write_excel(output_file)
        
        emit_status("Успешно выполнено!")
        emit_progress(100)
        
        return str(output_file)
        
    except Exception as e:
        error_message = f"Ошибка: {str(e)}\n{traceback.format_exc()}"
        emit_status(error_message)
        raise e