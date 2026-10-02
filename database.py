import pyodbc
from contextlib import contextmanager
try:
    from config import DB_CONFIG
except ImportError:
    # Fallback o mensaje de error si no existe el archivo de configuración
    DB_CONFIG = {
        "Driver": "{ODBC Driver 17 for SQL Server}",
        "Server": "SERVERHGON",
        "Database": "BDestadistica",
        "UID": "sa",
        "PWD": "password_here"
    }

def get_connection_string():
    """Genera la cadena de conexión basada en config.py"""
    return (
        f"Driver={DB_CONFIG['Driver']};"
        f"Server={DB_CONFIG['Server']};"
        f"Database={DB_CONFIG['Database']};"
        f"UID={DB_CONFIG['UID']};"
        f"PWD={DB_CONFIG['PWD']};"
    )

@contextmanager
def get_db_connection():
    """Manejador de contexto para conexiones seguras"""
    conn = None
    try:
        conn_str = get_connection_string()
        conn = pyodbc.connect(conn_str)
        yield conn
    except pyodbc.Error as e:
        print(f"Error de base de datos: {str(e)}")
        raise e
    finally:
        if conn:
            conn.close()

def execute_query(query, params=None):
    """Ejecuta una consulta y devuelve los resultados formateados como diccionarios"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
            
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
