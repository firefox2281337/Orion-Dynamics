import time
import psycopg2
import pyodbc
import oracledb

def check_database_status(config):
    status = "Недоступен"
    response_time = None
    
    try:
        start_time = time.time()
        if "port" in config and "dbname" in config:
            conn = psycopg2.connect(
                host=config["host"],
                port=config["port"],
                user=config["user"],
                password=config["password"],
                dbname=config["dbname"]
            )
        elif "driver" in config:
            conn = pyodbc.connect(
                f"DRIVER={config.get('driver', '')};"
                f"SERVER={config.get('server', '')};"
                f"DATABASE={config.get('database', '')};"
                f"Trusted_Connection={config.get('trusted_connection', '')};"
            )
        elif "dsn" in config:
            oracledb.init_oracle_client()
            conn = oracledb.connect(
                user=config["user"],
                password=config["password"],
                dsn=config["dsn"]
            )
        conn.close()
        response_time = round((time.time() - start_time) * 1000, 2)
        status = "Активен"
        return {
            "status": status,
            "response_time": response_time,
            "error": None
        }
    except Exception as e:
        status = "Недоступен"
        error_details = str(e)
        return {
            "status": status,
            "error": error_details,
            "response_time": response_time
        }