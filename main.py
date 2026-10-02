from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timedelta
import sys
import os
import mimetypes
import uvicorn
import threading
import time
import subprocess

# Ayudante para rutas en PyInstaller
def resource_path(relative_path):
    """ Obtiene la ruta absoluta para recursos, funciona para dev y PyInstaller """
    if getattr(sys, 'frozen', False):
        # Si corre como ejecutable, los recursos están en _MEIPASS
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# Ayudante para la ruta del ejecutable (donde está el .exe)
def get_exe_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

# Agregamos la ruta del EXE al path para poder importar config.py externo
sys.path.insert(0, get_exe_dir())

# Importaciones locales (ahora pueden ser externas)
try:
    from config import (
        SERVER_HOST, SERVER_PORT, VIDEOS_PATH,
        MONITOR_1_X, MONITOR_2_X, AUTO_OPEN_BROWSER, AUTO_OPEN_DELAY
    )
except ImportError:
    # Valores por defecto si no existe config.py
    SERVER_HOST = "0.0.0.0"
    SERVER_PORT = 8000
    VIDEOS_PATH = r"C:\VIDEOS"
    MONITOR_1_X = 0
    MONITOR_2_X = 1920
    AUTO_OPEN_BROWSER = True
    AUTO_OPEN_DELAY = 5

from database import execute_query
from queries import (
    QUERY_PACIENTES, 
    QUERY_RESUMEN_PACIENTES, 
    QUERY_FICHAS, 
    QUERY_MONITOR_FICHAS
)
mimetypes.add_type('video/mp4', '.mp4')

app = FastAPI(title="HGON Monitores API")

# Define la ruta física de tus videos
path_videos = VIDEOS_PATH
if os.path.exists(path_videos):
    app.mount("/galeria_videos", StaticFiles(directory=path_videos), name="videos_h")
else:
    print(f"ADVERTENCIA: No se encontró la ruta {path_videos}. Verifique el archivo config.py")

# Configuración de archivos estáticos y plantillas
app.mount("/static", StaticFiles(directory=resource_path("static")), name="static")
templates = Jinja2Templates(directory=resource_path("templates"))

@app.get("/api/videos")
async def list_videos():
    """Devuelve la lista de archivos .mp4 en la carpeta de videos"""
    try:
        if not os.path.exists(path_videos):
            return {"videos": [], "error": f"Ruta {path_videos} no encontrada"}
        
        videos = [f for f in os.listdir(path_videos) if f.lower().endswith('.mp4')]
        # Ordenamos los videos para que tengan un orden predecible o aleatorio en el front
        videos.sort()
        return {"videos": videos}
    except Exception as e:
        return {"videos": [], "error": str(e)}

@app.get("/internados", response_class=HTMLResponse)
async def read_pacientes(request: Request):
    """Ruta para el monitor de Pacientes Internados"""
    try:
        pacientes = execute_query(QUERY_PACIENTES)
        resumen_rows = execute_query(QUERY_RESUMEN_PACIENTES)
        
        conteo_unidades = {}
        for row in resumen_rows:
            unidad = str(row['Unidad']).strip().upper()
            total = int(row['Total_Pacientes'])
            conteo_unidades[unidad] = conteo_unidades.get(unidad, 0) + total
        
        total_internados = sum(conteo_unidades.values())

        return templates.TemplateResponse("pacientes_internados.html", {
            "request": request,
            "pacientes": pacientes,
            "total": total_internados,
            "resumen": conteo_unidades,
            "fecha_actual": datetime.now().strftime("%d %b %Y").upper()
        })
    except Exception as e:
        return HTMLResponse(
            content=f"<html><body><h1>Error de Conexión</h1><p>{str(e)}</p></body></html>", 
            status_code=500
        )

@app.get("/fichas", response_class=HTMLResponse)
async def read_fichas(request: Request):
    """Ruta para el monitor de Disponibilidad de Fichas"""
    try:
        fichas_raw = execute_query(QUERY_FICHAS)
        monitor_rows = execute_query(QUERY_MONITOR_FICHAS)
        
        hoy_date = datetime.now().date()
        if hoy_date.weekday() == 4: # Viernes
            manana_date = hoy_date + timedelta(days=3)
        elif hoy_date.weekday() == 5: # Sábado
            manana_date = hoy_date + timedelta(days=2)
        else:
            manana_date = hoy_date + timedelta(days=1)
            
        valid_dates = [hoy_date.strftime("%d/%m/%Y"), manana_date.strftime("%d/%m/%Y")]

        fichas_grouped = {}
        for f in fichas_raw:
            fecha_val = f['FECHA']
            fecha_str = str(fecha_val)
            if hasattr(fecha_val, "strftime"):
                fecha_str = fecha_val.strftime("%d/%m/%Y")
            elif isinstance(fecha_str, str) and "-" in fecha_str:
                parts = fecha_str.split("-")
                if len(parts) == 3:
                    fecha_str = f"{parts[2]}/{parts[1]}/{parts[0]}"
                    
            if fecha_str not in valid_dates:
                continue
                
            key = (f['ESPECIALIDAD'], f['MEDICO'], f['HORA_INI'], f['HORA_FIN'], f['TURNO'])
            if key not in fichas_grouped:
                fichas_grouped[key] = {
                    'ESPECIALIDAD': f['ESPECIALIDAD'],
                    'MEDICO': f['MEDICO'],
                    'FU_CODIGO': f['FU_CODIGO'],
                    'HORA_INI': f['HORA_INI'],
                    'HORA_FIN': f['HORA_FIN'],
                    'TURNO': f['TURNO'],
                    'FECHAS': [],
                    'TOTAL_GRP': 0,
                    'ASIGNADAS_GRP': 0,
                    'PENDIENTES_GRP': 0
                }
                    
            fichas_grouped[key]['FECHAS'].append({
                'FECHA': fecha_str,
                'TOTAL': f['TOTAL'],
                'ASIGNADAS': f['ASIGNADAS'],
                'PENDIENTES': f['PENDIENTES']
            })
            fichas_grouped[key]['TOTAL_GRP'] += int(f['TOTAL'] or 0)
            fichas_grouped[key]['ASIGNADAS_GRP'] += int(f['ASIGNADAS'] or 0)
            fichas_grouped[key]['PENDIENTES_GRP'] += int(f['PENDIENTES'] or 0)
        
        fichas = list(fichas_grouped.values())
        total_diarias = sum([f['TOTAL'] for f in fichas_raw]) if fichas_raw else 0
        
        # Procesamiento de lógica de monitor (mantenida de la versión anterior)
        medicos_dict = {}
        for row in monitor_rows:
            # Aseguramos tipos básicos
            medico_nombre = str(row.get('MEDICO', 'SIN NOMBRE')).strip()
            especialidad = str(row.get('ESPECIALIDAD', 'GENERAL')).strip()
            turno = str(row.get('TURNO', '--')).strip()
            # Helper to format time strings as HH:MM
            def format_time(val):
                if not val or val == '--:--': return '--:--'
                if hasattr(val, 'strftime'):
                    return val.strftime('%H:%M')
                s = str(val).strip()
                if ':' in s:
                    parts = s.split(':')
                    return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
                return s

            hora_ini = format_time(row.get('TUR_HORA_INI', '--:--'))
            hora_fin = format_time(row.get('TUR_HORA_FIN', '--:--'))
            fu_codigo = row.get('FU_CODIGO')
            
            key = (medico_nombre, especialidad, turno, hora_ini, hora_fin)
            if key not in medicos_dict:
                medicos_dict[key] = {
                    'MEDICO': medico_nombre,
                    'ESPECIALIDAD': especialidad,
                    'TURNO': turno,
                    'FU_CODIGO': fu_codigo,
                    'TUR_HORA_INI': hora_ini,
                    'TUR_HORA_FIN': hora_fin,
                    'ATENDIDAS': [],
                    'EN_ESPERA': [],
                    'AUSENTES': []
                }
            
            notif = str(row.get('NOTIFICACION', '')).strip().upper()
            try:
                ficha_val = int(row.get('FICHA', 0))
            except (ValueError, TypeError):
                ficha_val = 0

            if notif == 'ATENDIDO':
                medicos_dict[key]['ATENDIDAS'].append(ficha_val)
            elif notif == 'EN ESPERA':
                medicos_dict[key]['EN_ESPERA'].append(ficha_val)
            elif notif == 'AUSENTE':
                medicos_dict[key]['AUSENTES'].append(ficha_val)

        hora_actual = datetime.now()
        hora_actual_str = hora_actual.strftime("%H:%M")
        monitor_final = []
        for key, data in medicos_dict.items():
            turno = data['TURNO'].upper()
            
            # Ocultar médicos que no tengan un turno asignado en la base de datos
            if 'NO REG' in turno:
                continue
                
            # Ocultar turnos según el momento del día (Mañana < 12:00, Tarde >= 12:00)
            if hora_actual.hour >= 12 and turno == 'MAÑANA':
                continue
            if hora_actual.hour < 12 and turno == 'TARDE':
                continue
                
            # No mostrar turnos que ya terminaron (comparando la hora de fin con la hora actual)
            if data['TUR_HORA_FIN'] != '--:--' and data['TUR_HORA_FIN'] < hora_actual_str:
                continue


            max_atendido = max(data['ATENDIDAS']) if data['ATENDIDAS'] else 0
            
            # Lógica de colas (Siguiente / En Consultorio)
            # Priorizamos los números mayores al último atendido, luego rezagados, luego ausentes
            espera_normal = sorted([f for f in data['EN_ESPERA'] if f > max_atendido])
            espera_rezagados = sorted([f for f in data['EN_ESPERA'] if f <= max_atendido]) # <= por si acaso
            cola_espera = espera_normal + espera_rezagados + sorted(data['AUSENTES'])
            
            # Si ya finalizó con los pacientes (no hay nadie en cola de espera) ya no mostrar
            if not cola_espera:
                continue
            
            consultorio = cola_espera[0] if cola_espera else "--"
            siguiente = cola_espera[1] if len(cola_espera) > 1 else "--"
            
            # Buscar el total de fichas asignadas para hoy en fichas_raw
            total_pac = len(data['ATENDIDAS']) + len(data['EN_ESPERA']) + len(data['AUSENTES'])
            hoy_str_local = datetime.now().strftime("%d/%m/%Y")
            for raw_f in fichas_raw:
                f_fecha_val = raw_f.get('FECHA')
                f_fecha_str = str(f_fecha_val)
                if hasattr(f_fecha_val, "strftime"):
                    f_fecha_str = f_fecha_val.strftime("%d/%m/%Y")
                elif "-" in f_fecha_str:
                    parts = f_fecha_str.split("-")
                    if len(parts) == 3:
                        f_fecha_str = f"{parts[2]}/{parts[1]}/{parts[0]}"
                
                raw_hora_ini = format_time(raw_f.get('HORA_INI', '--:--'))
                
                if f_fecha_str == hoy_str_local and raw_f.get('FU_CODIGO') == data['FU_CODIGO'] and str(raw_f.get('TURNO', '')).upper() == data['TURNO'].upper() and raw_hora_ini == data['TUR_HORA_INI']:
                    total_pac = int(raw_f.get('TOTAL', 0) or 0)
                    break
            
            monitor_final.append({
                'MEDICO': data['MEDICO'],
                'ESPECIALIDAD': data['ESPECIALIDAD'],
                'TURNO': data['TURNO'],
                'FU_CODIGO': data['FU_CODIGO'],
                'TUR_HORA_INI': data['TUR_HORA_INI'],
                'TUR_HORA_FIN': data['TUR_HORA_FIN'],
                'ATENDIDO': max_atendido if max_atendido > 0 else "--",
                'CONSULTORIO': consultorio,
                'EN_ESPERA': siguiente,
                'TOTAL_PAC': total_pac
            })

        return templates.TemplateResponse("fichas_disponibilidad.html", {
            "request": request,
            "fichas": fichas,
            "monitor": monitor_final,
            "total_diarias": total_diarias,
            "fecha_actual": datetime.now().strftime("%d %b %Y").upper(),
            "hora_actual": datetime.now().strftime("%H:%M"),
            "hoy_str": datetime.now().strftime("%d/%m/%Y")
        })
    except Exception as e:
        return HTMLResponse(
            content=f"<html><body><h1>Error de Conexión</h1><p>{str(e)}</p></body></html>", 
            status_code=500
        )

def get_monitors_info():
    """Detecta las coordenadas X de todos los monitores usando la API de Windows"""
    if sys.platform != "win32":
        return []
        
    import ctypes
    user32 = ctypes.windll.user32
    
    class RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long),
                    ("top", ctypes.c_long),
                    ("right", ctypes.c_long),
                    ("bottom", ctypes.c_long)]

    def enum_handler(hMonitor, hdcMonitor, lprcMonitor, dwData):
        rect = lprcMonitor.contents
        monitors.append({'x': rect.left, 'y': rect.top, 'width': rect.right - rect.left, 'height': rect.bottom - rect.top})
        return True

    MONITORENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(RECT), ctypes.c_double)
    
    monitors = []
    user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(enum_handler), 0)
    # Ordenamos por posición X para identificar Izquierda -> Derecha
    monitors.sort(key=lambda m: m['x'])
    return monitors

def abrir_navegadores():
    """Lanza Chrome en las posiciones detectadas automáticamente"""
    if not AUTO_OPEN_BROWSER:
        return

    print(f"Detectando pantallas...")
    monitors = get_monitors_info()
    
    # Determinamos posiciones finales
    m1_x = MONITOR_1_X
    m2_x = MONITOR_2_X
    
    if len(monitors) >= 2:
        print(f"Se detectaron {len(monitors)} pantallas. Usando detección automática.")
        m1_x = monitors[0]['x']
        m2_x = monitors[1]['x']
    else:
        print(f"AVISO: Solo se detectó {len(monitors)} pantalla. Usando valores de respaldo de config.py.")

    print(f"Esperando {AUTO_OPEN_DELAY} segundos para abrir navegadores...")
    time.sleep(AUTO_OPEN_DELAY)
    
    base_url = f"http://localhost:{SERVER_PORT}"
    
    app_dir = os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, 'frozen', False) else os.getcwd()
    profile_1 = os.path.join(app_dir, "perfil_monitor_1")
    profile_2 = os.path.join(app_dir, "perfil_monitor_2")

    # Comando base para Chrome
    browser_cmd = "start chrome"
    flags = f'--new-window --start-fullscreen --autoplay-policy=no-user-gesture-required --disable-infobars --no-first-run'
    
    # Monitor 1 (Izquierda) - Internados
    cmd_1 = f'{browser_cmd} {flags} --user-data-dir="{profile_1}" --window-position={m1_x},0 {base_url}/internados'
    
    # Monitor 2 (Derecha) - Fichas
    cmd_2 = f'{browser_cmd} {flags} --user-data-dir="{profile_2}" --window-position={m2_x},0 {base_url}/fichas'
    
    try:
        if "--fichas-only" in sys.argv:
            print("Lanzando SOLAMENTE Monitor de Fichas...")
            subprocess.run(cmd_2, shell=True)
        elif "--internados-only" in sys.argv:
            print("Lanzando SOLAMENTE Monitor de Internados...")
            subprocess.run(cmd_1, shell=True)
        else:
            print(f"Lanzando pantallas en posiciones X: {m1_x} y {m2_x}")
            subprocess.run(cmd_1, shell=True)
            time.sleep(3) 
            subprocess.run(cmd_2, shell=True)
    except Exception as e:
        print(f"Error al abrir navegadores: {e}")

if __name__ == "__main__":
    # Iniciamos el hilo para abrir los navegadores
    thread_bus = threading.Thread(target=abrir_navegadores, daemon=True)
    thread_bus.start()
    
    # Iniciamos el servidor
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)