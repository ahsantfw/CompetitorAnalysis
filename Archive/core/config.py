import os
from urllib.parse import quote_plus
from pathlib import Path

# Try to load dotenv, but don't fail if it's not available
try:
    from dotenv import load_dotenv
    env_path = Path('.') / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except ImportError:
    # If python-dotenv is not installed, just continue without loading .env
    pass

SQL_SERVER = os.environ.get('SQL_SERVER')
SQL_DATABASE = os.environ.get('SQL_DATABASE')
SQL_USERNAME = os.environ.get('SQL_USERNAME')
SQL_PASSWORD = os.environ.get('SQL_PASSWORD')

# Build ODBC connection string for SQL Server
if SQL_SERVER and SQL_DATABASE and SQL_USERNAME and SQL_PASSWORD:
    sql_server = SQL_SERVER
    if ':' in sql_server:
        sql_server = sql_server.replace(':', ',')
    elif ',' not in sql_server:
        sql_server = f"{sql_server},1433"
    odbc_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={sql_server};"
        f"DATABASE={SQL_DATABASE};"
        f"UID={SQL_USERNAME};"
        f"PWD={SQL_PASSWORD};"
        "TrustServerCertificate=yes;"
        "Encrypt=yes;"
    )
    SQLALCHEMY_DATABASE_URL = f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_str)}"
else:
    SQLALCHEMY_DATABASE_URL = os.environ.get('SQL_DATABASE_URL', 'mssql+pyodbc:///?odbc_connect=DRIVER%3D%7BODBC+Driver+18+for+SQL+Server%7D%3BSERVER%3Dlocalhost%2C1433%3BDATABASE%3Dcompetitor%3BUID%3Duser%3BPWD%3Dpass%3BTrustServerCertificate%3Dyes%3BEncrypt%3Dyes%3B')

DATA_DIR = os.environ.get('DATA_DIR', 'data')
CHUNK_SIZE = int(os.environ.get('CHUNK_SIZE', 100_000)) 