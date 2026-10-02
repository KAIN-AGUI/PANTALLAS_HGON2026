# Configuración de Base de Datos
# Modifica estas variables si cambian tus credenciales

DB_CONFIG = {
    "Driver": "{ODBC Driver 17 for SQL Server}",
    "Server": "SERVERHGON",
    "Database": "BDestadistica",
    "UID": "sa",
    "PWD": "1029175026.hgon;"
}

# Configuración del servidor
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000

# Ruta física de los videos (puede ser local o unidad de red)
# Ejemplo: r"C:\Videos" o r"H:\PC-INTALADORES\video\VIDEOS"
VIDEOS_PATH = r"H:\PC-INTALADORES\video\VIDEOS"

# --- CONFIGURACIÓN DE PANTALLAS ---
# Ahora la aplicación detecta automáticamente la resolución de tus televisores.
# Estas variables se usarán solo si la detección automática falla.
MONITOR_1_X = 0      # Pantalla izquierda (Respaldo)
MONITOR_2_X = 1920   # Pantalla derecha (Respaldo)

# Abrir navegadores automáticamente (True/False)
AUTO_OPEN_BROWSER = True

# Tiempo de espera (segundos) antes de abrir los navegadores
AUTO_OPEN_DELAY = 5
