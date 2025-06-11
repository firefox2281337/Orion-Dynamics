import polars as pl
from web.templates.nexus.autoreg.logic.sql_operations import process_sql_query
from web.templates.nexus.autoreg.logic.data_processing_actuar2 import fetch_actuar2_data_in_chunks

def ensure_columns_exist(df, columns):
    for column in columns:
        if column not in df.columns:
            df = df.with_columns(pl.lit(None).alias(column))
    return df

def process_data_operations(df, phone_data, actuar2_data):
    from web.templates.nexus.autoreg.logic.handler_stubs import clean_column
    if df is None:
        raise ValueError("DataFrame (df) не инициализирован.")

    required_columns_pgsql = ["№ Договора К Пролонгации", "id физ лица", "Основной телефон", "Телефон 2",
        "Основной e-mail", "Дата рождения"]
    required_columns_actuar2 = ["№ Договора К Пролонгации", "Вид страхования", "Филиал ВСК", "Канал",
        "Объект страхования", "Прошлый период Страховая премия", "Прошлый период Страховая сумма", "Банк"]
    
    df = ensure_columns_exist(df, required_columns_pgsql)
    df = update_phone_numbers(df, phone_data)
    columns_to_clean = ["Основной телефон", "Телефон 2", "Телефон 3"]
    for col in columns_to_clean:
        if col in df.columns:
            df = df.with_columns(clean_column(pl.col(col)).alias(col))
    df = update_personal_data(df, phone_data)

    df = ensure_columns_exist(df, required_columns_actuar2)
    df = update_dataframe_from_actuar2(
        df,
        actuar2_data,
        mapping={
            "Вид страхования": 0, "Филиал ВСК": 1, "Канал": 2,
            "Объект страхования": 3, "Прошлый период Страховая премия": 5,
            "Прошлый период Страховая сумма": 4, "Вид полиса": 6, "Банк": 7})
    return df

def update_dataframe_from_actuar2(df, data_dict, mapping):
    updated_rows = []
    for row in df.iter_rows(named=True):
        contract_number = row["№ Договора К Пролонгации"]
        if contract_number in data_dict:
            data = data_dict[contract_number]
            for key, value in mapping.items():
                if row.get(key) is None or row.get(key) == "":
                    row[key] = data[value]
        updated_rows.append(row)
    return pl.DataFrame(updated_rows)

def fetch_actuar2_data(server_url, contract_numbers):
    return fetch_actuar2_data_in_chunks(server_url, contract_numbers)

def update_phone_numbers(df, data_dict):
    df = df.with_columns([
        pl.col("Основной телефон").cast(pl.Utf8).alias("Основной телефон"),
        pl.col("Телефон 2").cast(pl.Utf8).alias("Телефон 2"),
        pl.col("Телефон 3").cast(pl.Utf8).alias("Телефон 3")
    ])
    
    rows = df.to_dicts()
    updated_rows = []
    
    for row in rows:
        contract_number = row["№ Договора К Пролонгации"]
        if contract_number in data_dict:
            phone = str(data_dict[contract_number][1])
            phone2 = str(data_dict[contract_number][2])
            
            if row["Основной телефон"] is None or row["Основной телефон"] == "":
                if phone not in {row.get("Телефон 2"), row.get("Телефон 3")}:
                    row["Основной телефон"] = phone
                elif phone2 not in {row.get("Телефон 2"), row.get("Телефон 3")}:
                    row["Основной телефон"] = phone2
            
            if row["Телефон 2"] is None or row["Телефон 2"] == "":
                if phone not in {row.get("Основной телефон"), row.get("Телефон 3")}:
                    row["Телефон 2"] = phone
                elif phone2 not in {row.get("Основной телефон"), row.get("Телефон 3")}:
                    row["Телефон 2"] = phone2
            
            if row["Телефон 3"] is None or row["Телефон 3"] == "":
                if phone2 not in {row.get("Основной телефон"), row.get("Телефон 2")}:
                    row["Телефон 3"] = phone2
        
        updated_rows.append(row)
    return pl.DataFrame(updated_rows, schema=df.schema)

def update_personal_data(df, data_dict):
    updated_rows = []
    for row in df.iter_rows(named=True):
        contract_number = row["№ Договора К Пролонгации"]
        if contract_number in data_dict:
            data = data_dict[contract_number]
            if row.get("id физ лица") is None or row.get("id физ лица") == "":
                row["id физ лица"] = data[0]
            if row.get("Основной e-mail") is None or row.get("Основной e-mail") == "":
                row["Основной e-mail"] = data[3]
            if row.get("Дата рождения") is None or row.get("Дата рождения") == "":
                row["Дата рождения"] = data[5]
        updated_rows.append(row)
    return pl.DataFrame(updated_rows)

def process_data_pgsql(df, phone_data):
    from web.templates.nexus.autoreg.logic.handler_stubs import clean_column
    if df is None:
        raise ValueError("DataFrame (df) не инициализирован.")

    required_columns_pgsql = ["№ Договора К Пролонгации", "id физ лица", "Основной телефон", "Телефон 2",
        "Основной e-mail", "Дата рождения"]
    
    df = ensure_columns_exist(df, required_columns_pgsql)
    df = update_phone_numbers(df, phone_data)
    columns_to_clean = ["Основной телефон", "Телефон 2", "Телефон 3"]
    for col in columns_to_clean:
        if col in df.columns:
            df = df.with_columns(clean_column(pl.col(col)).alias(col))
    df = update_personal_data(df, phone_data)
    return df

def fetch_pgsql_data(server_url, contract_numbers):
    contracts_strs = ", ".join([f"('{contract}')" for contract in contract_numbers])
    df_pgsql = process_sql_query('C:/Users/EPopkov/Documents/Orion Dynamics/nexus/SQL/PostgreSQL.txt', server_url, "PostgreSQL", contracts_strs=contracts_strs)
    data_dict_pgsql = dict(zip(
        df_pgsql["contract_number"].to_list(),
        zip(df_pgsql["mdm_id"].to_list(), df_pgsql["phone"].to_list(), df_pgsql["phone2"].to_list(),
            df_pgsql["email"].to_list(), df_pgsql["email2"].to_list(), df_pgsql["birth"].to_list())))
    return data_dict_pgsql

