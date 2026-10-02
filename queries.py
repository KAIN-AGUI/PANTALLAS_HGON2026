# Consultas SQL para el Sistema HGON

QUERY_PACIENTES = """
SELECT  
    LTRIM(RTRIM(H.HCL_APPAT)) + ' ' + LTRIM(RTRIM(H.HCL_APMAT)) + ' ' + LTRIM(RTRIM(H.HCL_NOMBRE)) AS PACIENTE, 
    LTRIM(RTRIM(G.VGRUDESCRI)) AS UNIDAD_MEDICA, 
    RTRIM(S.SA_ENUM) as SALA,
    RTRIM(M.CAM_ENUM) as CAMA,
    CONVERT(VARCHAR(10), D.ORATDET_FECHAI, 103) as FECH_ING,
    CONVERT(VARCHAR(8), C.ORAT_FECHAOI, 108) as HORA
FROM SE_ORATENCAB C
INNER JOIN SE_ORATENDET D ON C.ORAT_CODIGO = D.ORAT_CODIGO
INNER JOIN SE_HC H ON C.HCL_CODIGO = H.HCL_CODIGO
INNER JOIN SE_CAMA M ON D.CAM_CODIGO = M.CAM_CODIGO
INNER JOIN SE_SALA S ON M.SA_CODIGO = S.SA_CODIGO
INNER JOIN (SELECT DISTINCT EMP_CODIGO, VGRUCODIGO, VGRUDESCRI FROM vgruposi) G 
    ON D.VGRUCODIGO = G.VGRUCODIGO AND G.EMP_CODIGO = 10
WHERE C.EMP_CODIGO = 10 AND D.ORATDET_EST = 'V' AND D.ORATDET_CODIGO = 1
ORDER BY D.ORATDET_FECHAI DESC, C.ORAT_FECHAOI DESC
"""

QUERY_RESUMEN_PACIENTES = """
SELECT 
    LTRIM(RTRIM(G.VGRUDESCRI)) AS Unidad,
    COUNT(DISTINCT h.HCL_CODIGO) AS Total_Pacientes
FROM 
    se_sala s
INNER JOIN se_cama c ON c.sa_codigo = s.sa_codigo
INNER JOIN VGRUPOSI g ON s.vgrucodigo = g.vgrucodigo
INNER JOIN SE_ORATENDET d ON d.CAM_CODIGO = c.CAM_CODIGO
INNER JOIN SE_ORATENcab ca ON d.EMP_CODIGO = ca.EMP_CODIGO AND d.ORAT_CODIGO = ca.ORAT_CODIGO
INNER JOIN se_hc h ON ca.EMP_CODIGO = h.EMP_CODIGO AND ca.HCL_CODIGO = h.HCL_CODIGO
WHERE 
    s.emp_codigo = 10 AND
    c.emp_codigo = 10 AND
    g.emp_codigo = 10 AND 
    d.ORATDET_EST = 'V'
GROUP BY 
    G.VGRUDESCRI
ORDER BY 
    G.VGRUDESCRI
"""

QUERY_FICHAS = """
SELECT 
    ESPECIALIDAD = CASE se.CUA_CODIGO
    WHEN 57 THEN 'ECOGRAFIA'
    WHEN 46 THEN 'FISIOTERAPIA'
    WHEN 44 THEN 'GENETICA MEDICA'
    WHEN 14 THEN 'NEANOTOLOGIA'
    WHEN 11 THEN 'OBSTETRICIA / GENECOLOGIA'
    WHEN 13 THEN 'MEDICINA INTERNA'
    WHEN 16 THEN 'PSICOLOGIA'
    ELSE LTRIM(RTRIM(se.CUA_DESCRIPCION))
END,
    MEDICO = CASE 
                WHEN p.pproCodPro IN (2,33,40,43,47,67) AND p.pperSexope = 0 THEN 'DR. '
                WHEN p.pproCodPro IN (2,33,40,43,47,67) AND p.pperSexope = 1 THEN 'DRA. '
                WHEN p.pproCodPro IN (60,74,76) THEN 'LIC. '
                ELSE '' 
             END + 
             RTRIM(p.pperNombre) + ', ' + RTRIM(p.pperPatern) + ' ' + RTRIM(p.pperMatern),
    FECHA = CAST(t.tur_fecha AS DATE), --  NUEVO: Para distinguir HOY vs MAÑANA
    HORA_INI = CONVERT(VARCHAR(5), t.tur_hora_ini, 108),
    HORA_FIN = CONVERT(VARCHAR(5), t.tur_hora_fin, 108),
    TURNO = CASE 
        WHEN CAST(t.tur_hora_ini AS TIME) < CAST('12:00:00' AS TIME) THEN 'MAÑANA'
        ELSE 'TARDE'
    END, 
    TOTAL = SUM(ISNULL(t.tur_fichas, 0)),
    ASIGNADAS = SUM(ISNULL(t.tur_fichas_actual, 0)),
    PENDIENTES = CASE 
        WHEN SUM(ISNULL(t.tur_fichas, 0)) - SUM(ISNULL(t.tur_fichas_actual, 0)) <= 0 THEN 0 
        ELSE SUM(ISNULL(t.tur_fichas, 0)) - SUM(ISNULL(t.tur_fichas_actual, 0)) 
    END,
    se.CUA_CODIGO,
    m.fu_codigo AS FU_CODIGO
FROM vSeleMedi m  
INNER JOIN BDrrhh.dbo.perPersona p ON m.fu_codigo = p.pperCodPer
INNER JOIN se_medico_cuaderno g ON m.emp_codigo = g.emp_codigo AND m.fu_codigo = g.med_codigo   
INNER JOIN se_cuaderno se ON se.CUA_CODIGO = g.Cua_codigo
INNER JOIN se_turno t ON g.cua_codigo = t.cua_codigo AND g.med_codigo = t.med_codigo
WHERE t.tur_fecha >= CAST(GETDATE() AS DATE) 
  AND t.tur_fecha < DATEADD(DAY, 5, CAST(GETDATE() AS DATE)) -- INCLUYE LOS PRÓXIMOS 5 DÍAS PARA CUBRIR FERIADOS/FINES DE SEMANA
GROUP BY 
    se.CUA_DESCRIPCION, 
    p.pproCodPro, p.pperSexope, p.pperPatern, p.pperMatern, p.pperNombre, 
    g.Med_codigo, 
    t.tur_fecha, 
    t.tur_hora_ini, 
    t.tur_hora_fin,
    se.CUA_CODIGO,
    m.fu_codigo
ORDER BY 
    t.tur_hora_ini,
    especialidad,MEDICO,FECHA,          -- Primero ordena por día
    TURNO 
    
"""

QUERY_MONITOR_FICHAS = """
SELECT 
    -- Numeramos por ficha dentro de cada bloque de horario de inicio del médico
    ROW_NUMBER() OVER(
        PARTITION BY MED_CODIGO, CUA_CODIGO, TURNO, TUR_HORA_INI 
        ORDER BY DAT_FILA
    ) AS FICHA, 

    FU_CODIGO,  -- 👈 NUEVO CAMPO

    PACIENTE,
    ESPECIALIDAD,
    MEDICO,
    TURNO,
    ISNULL(TUR_HORA_INI, '') AS TUR_HORA_INI, 
    ISNULL(TUR_HORA_FIN, '') AS TUR_HORA_FIN, 

    CASE 
        WHEN VALOR_FINAL = 'S' THEN 'AUSENTE'
        WHEN LEN(RTRIM(VALOR_FINAL)) > 0 THEN 'ATENDIDO'
        ELSE 'EN ESPERA'
    END AS NOTIFICACION,

    VALOR_FINAL AS VALOR_REGISTRADO

FROM (
    SELECT 
        d.DAT_FILA, 

        -- 👇 NUEVO
        d.med_codigo AS FU_CODIGO,

        (RTRIM(hc.HCL_APPAT) + ' ' + RTRIM(hc.HCL_APMAT) + ' ' + RTRIM(hc.HCL_NOMBRE)) AS PACIENTE,
        
        CASE 
            WHEN LTRIM(RTRIM(se.CUA_DESCRIPCION)) = 'CE. GINECOLOGIA' THEN 'OBSTETRICIA/GENECOLOGIA'
            WHEN LTRIM(RTRIM(se.CUA_DESCRIPCION)) = 'CE. GENETICA MEDICA' THEN 'GENETICA MEDICA'
            WHEN LTRIM(RTRIM(se.CUA_DESCRIPCION)) = 'CE. MEDICINA INTERNA' THEN 'MEDICINA INTERNA'
            WHEN LTRIM(RTRIM(se.CUA_DESCRIPCION)) = 'CE. NEONATOLOGIA' THEN 'NEONATOLOGIA'
            ELSE LTRIM(RTRIM(se.CUA_DESCRIPCION))
        END AS ESPECIALIDAD,

        CASE 
            WHEN p.pproCodPro IN (2,33,40) AND p.pperSexope = 0 THEN 'DR. '
            WHEN p.pproCodPro IN (2,33,40) AND p.pperSexope = 1 THEN 'DRA. '
            WHEN p.pproCodPro IN (74,76) THEN 'LIC. '
            ELSE '' 
        END + RTRIM(p.pperNombre) + ', ' + RTRIM(p.pperPatern) + ' ' + RTRIM(p.pperMatern) AS MEDICO,

        f.CUA_CODIGO,
        d.med_codigo AS MED_CODIGO,

        ISNULL(T_UNICO.TURNO, 'NO REGISTRADO') AS TURNO,

        CONVERT(VARCHAR(5), T_UNICO.tur_hora_ini, 108) AS TUR_HORA_INI, 
        CONVERT(VARCHAR(5), T_UNICO.tur_hora_fin, 108) AS TUR_HORA_FIN, 

        COALESCE(
            MAX(CASE WHEN f.FOR_CODIGO = 3134 THEN VALOR END),
            MAX(CASE WHEN f.FOR_CODIGO = 3138 THEN VALOR END),
            MAX(CASE WHEN f.FOR_CODIGO = 3204 THEN VALOR END),
            MAX(CASE WHEN f.FOR_CODIGO = 4633 THEN VALOR END),
            ''
        ) AS VALOR_FINAL

    FROM se_datos d
    INNER JOIN se_formulario f ON f.for_codigo = d.for_codigo
    INNER JOIN se_columnas c ON f.col_codigo = c.col_codigo
    INNER JOIN se_hc hc ON d.HCL_CODIGO = hc.HCL_CODIGO AND hc.emp_codigo = d.emp_codigo
    INNER JOIN se_cuaderno se ON f.CUA_CODIGO = se.CUA_CODIGO
    INNER JOIN BDrrhh.dbo.perPersona p ON d.med_codigo = p.pperCodPer

    CROSS APPLY (
        SELECT dbo.fn_se_datos_sel(
            c.COL_TIPO, 
            d.EMP_CODIGO, 
            d.DAT_DATA, 
            c.col_AUXILIAR, 
            c.rel_codigo, 
            f.FOR_CODIGO
        ) AS VALOR
    ) X

    OUTER APPLY (
        SELECT TOP 1 
            CASE 
                WHEN CAST(t.tur_hora_ini AS TIME) < '12:00:00' THEN 'MAÑANA'
                ELSE 'TARDE'
            END AS TURNO,
            t.tur_hora_ini, 
            t.tur_hora_fin  
        FROM se_turno t
        WHERE t.CUA_CODIGO = f.CUA_CODIGO 
          AND t.med_codigo = d.med_codigo
          AND CAST(t.tur_fecha AS DATE) = CAST(d.dat_fecha AS DATE)
          AND (
            CAST(d.dat_fecha AS TIME) = '00:00:00' 
            OR 
            (CAST(d.dat_fecha AS TIME) >= CAST(t.tur_hora_ini AS TIME) 
             AND CAST(d.dat_fecha AS TIME) <= CAST(t.tur_hora_fin AS TIME))
          )
        ORDER BY t.tur_hora_ini ASC
    ) AS T_UNICO

    WHERE d.emp_codigo = 10 
      AND d.dat_fecha >= CAST(GETDATE() AS DATE) 
      AND d.dat_fecha < DATEADD(DAY, 1, CAST(GETDATE() AS DATE))
      AND f.CUA_CODIGO NOT IN (16,17,20,27,29,32,36,46,47,64,69,2000) 

    GROUP BY 
        d.DAT_FILA, 
        hc.HCL_APPAT, hc.HCL_APMAT, hc.HCL_NOMBRE,
        f.CUA_CODIGO, 
        d.med_codigo, 
        se.CUA_DESCRIPCION,
        p.pproCodPro, p.pperSexope, p.pperNombre, p.pperPatern, p.pperMatern,
        T_UNICO.TURNO, 
        T_UNICO.tur_hora_ini, 
        T_UNICO.tur_hora_fin  

) AS Subconsulta

ORDER BY 
    TURNO ASC, 
    TUR_HORA_INI ASC, 
    MEDICO, 
    FICHA;
"""
