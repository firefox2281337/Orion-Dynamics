import polars as pl
from web.templates.nexus.autoreg.logic.sql_operations import load_sql_query, execute_sql_query 

def fetch_actuar2_data(server_url, contract_chunks):
    data_dict_actuar2 = {}
    for chunk in contract_chunks:
        contracts_str = ", ".join([f"'{contract}'" for contract in chunk])
        sql_query = load_sql_query('C:/Users/EPopkov/Documents/Orion Dynamics/nexus/SQL/ACTUAR2.txt', contracts_strss=contracts_str)
        response_data = execute_sql_query(server_url, "ACTUAR2", sql_query)
        results = response_data['results'][0]
        columns = results['columns']
        rows = results['rows']
        temp_df = pl.DataFrame(rows, schema={col: str for col in columns})
        temp_dict = dict(zip(
            temp_df["Номер договора к пролонгации"].to_list(), zip(
                temp_df["Вид страхования"].to_list(),
                temp_df["Наименование филиала"].to_list(),
                temp_df["Канал продаж"].to_list(),
                temp_df["Адрес"].to_list(),
                temp_df["Страховая премия"].to_list(),
                temp_df["Премия начисленная"].to_list(),
                temp_df["Срок жизни договора"].to_list(),
                temp_df["Банк"].to_list())))
        data_dict_actuar2.update(temp_dict)
    return data_dict_actuar2

def fetch_actuar2_data_in_chunks(server_url, contract_numbers, chunk_size=20000):
    contract_chunks = [contract_numbers[i:i + chunk_size] for i in range(0, len(contract_numbers), chunk_size)]
    return fetch_actuar2_data(server_url, contract_chunks)