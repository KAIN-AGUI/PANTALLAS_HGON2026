import streamlit as st
import pandas as pd
import pyodbc
import time
import base64

def get_img_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

imagen_base64 = get_img_base64("C:/Users/Info Computers/Desktop/NUMERO DE FICHA/medico.jpg")

# 1. CONFIGURACIÓN DE PANTALLA
st.set_page_config(page_title="Monitor de Sala de Espera", layout="wide", initial_sidebar_state="collapsed")

# 2. ESTILOS CSS OPTIMIZADOS PARA CENTRADO Y RESALTADO
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .block-container {
        padding-top: 0.5rem;
        background-color: white;
    }

    .monitor-table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'Arial Black', sans-serif;
        border: 6px solid black;
    }
    
    .monitor-header {
        background-color: #f2f2f2;
        color: black;
        text-align: center;
        padding: 15px;
        font-size: 2.5rem !important;
        border: 6px solid black;
    }

    .medico-cell {
        font-size: 3.2rem !important;
        color: black !important;
        font-weight: bold;
        padding: 20px;
        border: 6px solid black;
        width: 50%;
        height: 120px;
        vertical-align: middle;
        line-height: 1.1;
        background-color: #fafafa;
    }
    
    .imagen-cell {
        text-align: center;
        padding: 20px;
        border: 6px solid black;
        width: 50%;
        height: 120px;
        vertical-align: middle;
        background-color: #ffffff;
    }
    
    .imagen-hospital {
        max-width: 100%;
        max-height: 150px;
        object-fit: contain;
    }

    .especialidad-text {
        font-size: 1.8rem !important;
        color: #d32f2f !important;
        font-weight: bold;
        display: block;
        margin-top: 10px;
        text-transform: uppercase;
    }

    /* ETIQUETA FICHA CENTRADA Y RESALTADA */
    .container-ficha {
        text-align: center; /* Centra todo el contenido de la celda */
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }

    .label-ficha {
        font-size: 2.2rem !important;
        color: white !important;
        font-weight: bold;
        background-color: #444; /* Gris oscuro plomo */
        padding: 2px 20px;
        border-radius: 8px;
        display: inline-block;
        margin-bottom: 5px; /* Acerca la etiqueta al número */
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
        text-transform: uppercase;
    }

    .number-cell {
        font-size: 10rem !important;
        color: black !important;
        font-weight: bold;
        text-align: center;
        border: 6px solid black;
        padding: 10px 0;
        width: 33.3%;
        line-height: 0.9;
    }
    
    .status-cell {
        font-size: 2rem !important;
        font-weight: bold;
        text-align: center;
        border: 6px solid black;
        padding: 20px;
        text-transform: uppercase;
    }

    /* Colores para estados */
    .bg-atendido { background-color: #28a745 !important; color: white !important; }
    .bg-consultorio { background-color: #ffc107 !important; color: black !important; }
    .bg-espera { background-color: #17a2b8 !important; color: white !important; }
    
    /* Fondos para los números */
    .num-atendido { background-color: #e8f5e9; }
    .num-consultorio { background-color: #fff9e6; }
    .num-espera { background-color: #e1f5fe; }
    </style>
    """, unsafe_allow_html=True)

# 3. OBTENCIÓN DE DATOS
def get_data():
    server = 'SERVERHGON\\SERVERSQL'
    database = 'BDestadistica'
    username = 'sa'
    password = '1029175026.hgon'
    
    conn_str = f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'
    
    query = """
    SELECT 
        -- Se agrega TURNO al PARTITION BY para que la numeración sea independiente por turno
        ROW_NUMBER() OVER(PARTITION BY MED_CODIGO, CUA_CODIGO, TURNO ORDER BY DAT_FILA) AS FICHA, 
        PACIENTE,
        ESPECIALIDAD,
        MEDICO,
        TURNO,
        NOTIFICACION,
        VALOR_REGISTRADO
    FROM (
        SELECT 
            d.DAT_FILA, 
            (RTRIM(hc.HCL_APPAT) + ' ' + RTRIM(hc.HCL_APMAT) + ' ' + RTRIM(hc.HCL_NOMBRE)) AS PACIENTE,
            RTRIM(se.CUA_DESCRIPCION) AS ESPECIALIDAD,
            CASE 
                WHEN p.pproCodPro IN (2,33,40) AND p.pperSexope = 0 THEN 'DR. '
                WHEN p.pproCodPro IN (2,33,40) AND p.pperSexope = 1 THEN 'DRA. '
                WHEN p.pproCodPro = 76 THEN 'LIC. '
                ELSE '' 
            END + RTRIM(p.pperNombre) + ', ' + RTRIM(p.pperPatern) + ' ' + RTRIM(p.pperMatern) AS MEDICO,
            f.CUA_CODIGO,
            d.med_codigo AS MED_CODIGO,
            T_UNICO.TURNO,
            CASE 
                WHEN MAX(CASE WHEN f.FOR_CODIGO = 3134 THEN dbo.fn_se_datos_sel(c.COL_TIPO, d.EMP_CODIGO, d.DAT_DATA, c.col_AUXILIAR, c.rel_codigo, f.FOR_CODIGO) ELSE '' END) = 'S' THEN 'AUSENTE'
                WHEN LEN(RTRIM(MAX(CASE WHEN f.FOR_CODIGO = 3134 THEN dbo.fn_se_datos_sel(c.COL_TIPO, d.EMP_CODIGO, d.DAT_DATA, c.col_AUXILIAR, c.rel_codigo, f.FOR_CODIGO) ELSE '' END))) > 0 THEN 'ATENDIDO'
                ELSE 'EN ESPERA'
            END AS NOTIFICACION,
            MAX(CASE WHEN f.FOR_CODIGO = 3134 
                     THEN dbo.fn_se_datos_sel(c.COL_TIPO, d.EMP_CODIGO, d.DAT_DATA, c.col_AUXILIAR, c.rel_codigo, f.FOR_CODIGO) 
                     ELSE '' END) AS VALOR_REGISTRADO
            
        FROM se_datos d
        INNER JOIN se_formulario f ON f.for_codigo = d.for_codigo
        INNER JOIN se_columnas c ON f.col_codigo = c.col_codigo
        INNER JOIN se_hc hc ON d.HCL_CODIGO = hc.HCL_CODIGO AND hc.emp_codigo = d.emp_codigo
        INNER JOIN se_cuaderno se ON f.CUA_CODIGO = se.CUA_CODIGO
        INNER JOIN BDrrhh.dbo.perPersona p ON d.med_codigo = p.pperCodPer
        
        CROSS APPLY (
            SELECT TOP 1 
                CASE 
                    WHEN CAST(t.tur_hora_ini AS TIME) < CAST('12:00:00' AS TIME) THEN 'MAÑANA'
                    ELSE 'TARDE'
                END AS TURNO
            FROM se_turno t
            WHERE t.CUA_CODIGO = f.CUA_CODIGO 
              AND t.med_codigo = d.med_codigo
        ) AS T_UNICO

        WHERE d.emp_codigo = 10 
          AND d.dat_fecha >= CAST(GETDATE() AS DATE) 
          AND d.dat_fecha < DATEADD(day, 1, CAST(GETDATE() AS DATE))
          AND f.CUA_CODIGO NOT IN (16,17,27,29,36,32,46,20,64,69) 
        GROUP BY 
            d.DAT_FILA, hc.HCL_APPAT, hc.HCL_APMAT, hc.HCL_NOMBRE,
            f.CUA_CODIGO, d.med_codigo, se.CUA_DESCRIPCION,
            p.pproCodPro, p.pperSexope, p.pperNombre, p.pperPatern, p.pperMatern,
            T_UNICO.TURNO
    ) AS Subconsulta
    ORDER BY TURNO ASC, MEDICO, ESPECIALIDAD, FICHA
    """
    try:
        conn = pyodbc.connect(conn_str, timeout=10)
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"⚠️ ERROR DE CONEXIÓN: {e}")
        return None

# 4. LÓGICA DE ROTACIÓN
if 'idx' not in st.session_state:
    st.session_state.idx = 0

df = get_data()

if df is not None and not df.empty:
    # Asegurar que no hay espacios en blanco ocultos desde SQL
    df['NOTIFICACION'] = df['NOTIFICACION'].astype(str).str.strip()
    
    # Incluimos AUSENTE en la lista válida para que el sistema los mantenga en cola
    df_valid = df[df['NOTIFICACION'].isin(['ATENDIDO', 'EN ESPERA', 'AUSENTE'])]
    
    # Obtenemos combinaciones únicas de médico, especialidad y turno para evitar mezcla de fichas
    df_turnos = df_valid[['MEDICO', 'ESPECIALIDAD', 'TURNO']].drop_duplicates()
    lista_turnos = df_turnos.values.tolist()
    
    if len(lista_turnos) > 0:
        # Seleccionamos el turno actual (Médico, Especialidad, Turno) basado en el índice de rotación
        turno_act = lista_turnos[st.session_state.idx % len(lista_turnos)]
        med_act, especialidad_act, turno_horario = turno_act
        
        # Filtramos por los tres criterios para que las fichas no se repitan en distintos turnos
        df_m = df_valid[(df_valid['MEDICO'] == med_act) & 
                        (df_valid['ESPECIALIDAD'] == especialidad_act) & 
                        (df_valid['TURNO'] == turno_horario)]
        
        # 1. Identificamos el máximo atendido hasta ahora
        max_atendido_val = df_m[df_m['NOTIFICACION'] == 'ATENDIDO']['FICHA'].max()
        max_atendido_num = int(max_atendido_val) if pd.notna(max_atendido_val) else 0
        
        # 2. Lista de pacientes en espera separada en prioridades
        # A) Normales: 'EN ESPERA' pero con ficha MAYOR que la última atendida (no han sido llamados)
        espera_normal = sorted(df_m[(df_m['NOTIFICACION'] == 'EN ESPERA') & (df_m['FICHA'] > max_atendido_num)]['FICHA'].tolist())
        
        # B) Rezagados: 'EN ESPERA' pero con ficha MENOR a la última atendida 
        # (fueron saltados por el médico pero no los marcó explícitamente como 'AUSENTE')
        espera_rezagados = sorted(df_m[(df_m['NOTIFICACION'] == 'EN ESPERA') & (df_m['FICHA'] < max_atendido_num)]['FICHA'].tolist())
        
        # C) Ausentes: Explícitamente marcados 'AUSENTE' por el médico
        espera_ausentes = sorted(df_m[df_m['NOTIFICACION'] == 'AUSENTE']['FICHA'].tolist())
        
        # Combinamos: Los normales pasan primero. Rezagados y ausentes pasan al final de la cola.
        espera_list = espera_normal + espera_rezagados + espera_ausentes
        
        if max_atendido_num == 0:
            # CASO INICIAL: Nadie ha sido atendido aún (Estado 0, 1, 2)
            atendido = 0
            consultorio = int(espera_list[0]) if len(espera_list) > 0 else "--"
            en_espera = int(espera_list[1]) if len(espera_list) > 1 else "--"
        else:
            # CASO GENERAL (incluye emergencias y saltos)
            # ATENDIDA: La ficha con número más alto que ya terminó (o la última procesada)
            atendido = max_atendido_num
            # EN CONSULTORIO: La primera persona en la fila de espera actual
            consultorio = int(espera_list[0]) if len(espera_list) > 0 else "--"
            # SIGUIENTE: El que está detrás del paciente en consultorio
            en_espera = int(espera_list[1]) if len(espera_list) > 1 else "--"
        
        st.markdown(f"""
        <table class="monitor-table" style="width:100%;">
            <tr>
                <td class="medico-cell">
                    {med_act.replace(', ', ',<br>')}
                    <span class="especialidad-text">{especialidad_act} - TURNO {turno_horario}</span>
                </td>
                <td class="imagen-cell">
                    <img src="data:image/jpeg;base64,{imagen_base64}" class="imagen-hospital" alt="Hospital">
                </td>
            </tr>
        </table>
        
        <table class="monitor-table" style="width:100%; margin-top:0;">
            <tr>
                <td class="number-cell num-atendido">
                    <div class="container-ficha">
                        <span class="label-ficha">FICHA</span>
                        <span>{atendido}</span>
                    </div>
                </td>
                <td class="number-cell num-consultorio">
                    <div class="container-ficha">
                        <span class="label-ficha">FICHA</span>
                        <span>{consultorio}</span>
                    </div>
                </td>
                <td class="number-cell num-espera" style="border-right:none;">
                    <div class="container-ficha">
                        <span class="label-ficha">FICHA</span>
                        <span>{en_espera}</span>
                    </div>
                </td>
            </tr>
            <tr>
                <td class="status-cell bg-atendido">ATENDIDA</td>
                <td class="status-cell bg-consultorio">EN CONSULTORIO</td>
                <td class="status-cell bg-espera" style="border-right:none;">SIGUIENTE</td>
            </tr>
        </table>
        """, unsafe_allow_html=True)

        st.session_state.idx += 1
        time.sleep(10)
        st.rerun()
    else:
        st.info("No hay pacientes en espera actualmente.")
        time.sleep(5)
        st.rerun()