import requests
import polars as pl

def load_sql_query(file_path, **kwargs):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read().format(**kwargs).replace("\n", " ")

def execute_sql_query(server_url, database, sql_query):
    response = requests.post(
        server_url,
        json={"query": sql_query, "database": database},
        headers={"Content-Type": "application/json"})
    if response.status_code != 200:
        raise Exception(f"Ошибка запроса: {response.status_code}, {response.text}")
    return response.json()

def process_sql_query(file_path, server_url, database, **kwargs):
    sql_query = load_sql_query(file_path, **kwargs)
    response_data = execute_sql_query(server_url, database, sql_query)
    if not response_data.get("columns") or not response_data.get("rows"):
        raise ValueError("Нет данных в ответе сервера.")
    return pl.DataFrame(response_data["rows"], schema={col: str for col in response_data["columns"]})