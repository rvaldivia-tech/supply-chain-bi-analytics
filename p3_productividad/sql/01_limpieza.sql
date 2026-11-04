-- ============================================================
-- 01_limpieza.sql
-- picking_limpio: filas únicas y normalizadas, con un estado de validez.
-- Nota: UPPER/LOWER de SQLite solo cambian letras ASCII (no convierten Ñ),
--       por eso el turno se normaliza por su primera letra.
-- ============================================================

DROP TABLE IF EXISTS operadores;
CREATE TABLE operadores AS
SELECT id_operador, turno_asignado,
       CAST(antiguedad_meses_inicio AS INTEGER) AS antiguedad_meses_inicio,
       zona_principal
FROM operadores_raw;

DROP TABLE IF EXISTS metas;
CREATE TABLE metas AS
SELECT zona, CAST(meta_lineas_hora AS REAL) AS meta_lineas_hora FROM metas_raw;

DROP TABLE IF EXISTS picking_limpio;
CREATE TABLE picking_limpio AS
WITH n AS (
    SELECT
        id_registro,
        CASE WHEN fecha LIKE '__/__/____'
             THEN substr(fecha,7,4)||'-'||substr(fecha,4,2)||'-'||substr(fecha,1,2)
             ELSE fecha END                                           AS fecha,
        id_operador,
        CASE UPPER(substr(TRIM(turno), 1, 1))
             WHEN 'M' THEN 'Mañana'
             WHEN 'T' THEN 'Tarde'
             WHEN 'N' THEN 'Noche' END                                AS turno,
        zona,
        CAST(NULLIF(TRIM(lineas), '') AS INTEGER)                     AS lineas,
        CAST(unidades AS INTEGER)                                     AS unidades,
        CAST(NULLIF(TRIM(horas), '') AS REAL)                         AS horas,
        CAST(errores AS INTEGER)                                      AS errores,
        ROW_NUMBER() OVER (PARTITION BY id_registro ORDER BY rowid)   AS rn
    FROM picking_raw
)
SELECT id_registro, fecha, id_operador, turno, zona, lineas, unidades, horas, errores,
       CASE WHEN horas IS NULL OR horas = 0 THEN 'SIN_HORAS'
            WHEN horas > 12                 THEN 'HORAS_ATIPICAS'
            WHEN lineas IS NULL OR lineas < 0 THEN 'LINEAS_INVALIDAS'
            ELSE 'VALIDO' END                                         AS estado
FROM n WHERE rn = 1;

INSERT INTO calidad_datos
SELECT 'Registros válidos para KPIs', COUNT(*), 'Base de los KPIs'
FROM picking_limpio WHERE estado = 'VALIDO';
