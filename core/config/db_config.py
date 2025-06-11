DATABASES = {
    "PostgreSQL": {
        "host": "ma-db-prod.vsk.ru",
        "port": 5432,
        "user": "epopkov",
        "password": "eW9SCYs9",
        "dbname": "marketing"
    },
    "ACTUAR2": {
        "driver": "{ODBC Driver 17 for SQL Server}",
        "server": "ACTUAR2",
        "database": "Controlling",
        "trusted_connection": "yes"
    },
    "Oracle": {
        "dsn": "adinsure-db-node3:1521/ADACTA",
        "user": "EPOPKOV",
        "password": "b6SkzyMEp4hj"
    },
    "adinsure_prod": {
        "driver": "{ODBC Driver 17 for SQL Server}",
        "server": "axcdbrep1\\cdbrep1",
        "database": "dstrah",
        "trusted_connection": "yes"
    }
}

ALLOWED_IPS = ["192.168.50.220", "192.168.50.192", "192.168.50.119", "192.168.51.27", "192.168.51.128", "192.168.50.172", "192.168.51.182"]
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
SECRET_KEY = "36d1eecee67dea664ca9c1a68c0dda64"
DATA_PATH = 'web/data/files.json'
FILES_DIR = 'web/static/files'
UPLOAD_FOLDER = 'web/static/files'

def get_database_config(db_name):
    return DATABASES.get(db_name)