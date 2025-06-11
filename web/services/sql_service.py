# web/services/sql_service.py
"""
Сервис для выполнения SQL операций
"""

import hashlib
import traceback
import pyodbc
import psycopg2
import oracledb
from core.config.db_config import DATABASES
from web.utils.logging_helper import log_error


class SQLService:
    """Сервис для работы с SQL"""
    
    def __init__(self):
        self.databases = DATABASES
    
    def execute_sql(self, sql_query, database):
        """
        Выполняет SQL запрос к указанной базе данных
        
        Args:
            sql_query: SQL запрос
            database: Название базы данных
            
        Returns:
            dict: Результат выполнения запроса
        """
        try:
            if database not in self.databases:
                return {"error": "Выбрана неверная база данных."}
            
            if database == "PostgreSQL":
                return self._execute_postgresql(sql_query)
            elif database in ["ACTUAR2", "adinsure_prod"]:
                return self._execute_mssql(sql_query, database)
            elif database == "Oracle":
                return self._execute_oracle(sql_query)
            else:
                return {"error": f"База данных {database} не поддерживается."}
                
        except Exception as e:
            log_error(f"Ошибка выполнения SQL запроса: {str(e)}", traceback_info=traceback.format_exc())
            return {"error": f"Ошибка выполнения запроса: {str(e)}"}
    
    def _execute_postgresql(self, sql_query):
        """Выполнение запроса к PostgreSQL"""
        conn = psycopg2.connect(**self.databases["PostgreSQL"])
        cursor = conn.cursor()
        
        try:
            cursor.execute(sql_query)
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                result = {
                    "columns": columns,
                    "rows": [dict(zip(columns, row)) for row in rows]
                }
            else:
                result = {"message": "Запрос выполнен, но данных нет."}
        finally:
            cursor.close()
            conn.close()
        
        return result
    
    def _execute_mssql(self, sql_query, database):
        """Выполнение запроса к MS SQL Server"""
        config = self.databases[database]
        conn = pyodbc.connect(
            f"DRIVER={config['driver']};"
            f"SERVER={config['server']};"
            f"DATABASE={config['database']};"
            f"Trusted_Connection={config['trusted_connection']};"
        )
        cursor = conn.cursor()
        
        try:
            cursor.execute(sql_query)
            results = []
            
            while True:
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    results.append({
                        "columns": columns,
                        "rows": [dict(zip(columns, row)) for row in rows]
                    })
                if not cursor.nextset():
                    break
            
            result = {"results": results}
        finally:
            cursor.close()
            conn.close()
        
        return result
    
    def _execute_oracle(self, sql_query):
        """Выполнение запроса к Oracle"""
        conn = oracledb.connect(
            user=self.databases["Oracle"]["user"],
            password=self.databases["Oracle"]["password"],
            dsn=self.databases["Oracle"]["dsn"]
        )
        cursor = conn.cursor()
        
        try:
            cursor.execute(sql_query)
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                result = {
                    "columns": columns,
                    "rows": [dict(zip(columns, row)) for row in rows]
                }
            else:
                result = {"message": "Запрос выполнен, но данных нет."}
        finally:
            cursor.close()
            conn.close()
        
        return result
    
    def execute_query_api(self, sql_query, database):
        """
        Выполнение запроса через API (для внешних вызовов)
        
        Args:
            sql_query: SQL запрос
            database: База данных
            
        Returns:
            dict: Результат запроса в формате API
        """
        try:
            if database == "PostgreSQL":
                conn = psycopg2.connect(**self.databases["PostgreSQL"])
                cursor = conn.cursor()
                
                cursor.execute(sql_query)
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    result = {
                        "columns": columns,
                        "rows": [dict(zip(columns, row)) for row in rows]
                    }
                else:
                    result = {"message": "Запрос выполнен, но данных нет."}
                
                cursor.close()
                conn.close()
                return result
                
            elif database in ["ACTUAR2", "adinsure_prod"]:
                config = self.databases[database]
                conn = pyodbc.connect(
                    f"DRIVER={config['driver']};"
                    f"SERVER={config['server']};"
                    f"DATABASE={config['database']};"
                    f"Trusted_Connection={config['trusted_connection']};"
                )
                cursor = conn.cursor()
                cursor.execute(sql_query)
                
                results = []
                while True:
                    if cursor.description:
                        columns = [desc[0] for desc in cursor.description]
                        rows = cursor.fetchall()
                        results.append({
                            "columns": columns,
                            "rows": [dict(zip(columns, row)) for row in rows]
                        })
                    if not cursor.nextset():
                        break
                
                cursor.close()
                conn.close()
                return {"results": results}
                
            elif database == "Oracle":
                conn = oracledb.connect(
                    user=self.databases["Oracle"]["user"],
                    password=self.databases["Oracle"]["password"],
                    dsn=self.databases["Oracle"]["dsn"]
                )
                cursor = conn.cursor()
                
                cursor.execute(sql_query)
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    result = {
                        "columns": columns,
                        "rows": [dict(zip(columns, row)) for row in rows]
                    }
                else:
                    result = {"message": "Запрос выполнен, но данных нет."}
                
                cursor.close()
                conn.close()
                return result
                
            else:
                return {"error": f"База данных {database} не поддерживается."}
                
        except Exception as e:
            error_message = f"Ошибка выполнения запроса: {str(e)}\n{traceback.format_exc()}"
            log_error(error_message)
            return {"error": error_message}
    
    def get_query_hash(self, sql_query):
        """Получение хеша SQL запроса для логирования"""
        return hashlib.md5(sql_query.encode('utf-8')).hexdigest()