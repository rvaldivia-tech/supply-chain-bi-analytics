-- ============================================================
-- 02_kpis.sql
-- Definiciones:
--   Líneas por hora (LPH) = SUM(líneas) / SUM(horas)         <- promedio PONDERADO
--   Unidades por hora     = SUM(unidades) / SUM(horas)
--   Error rate            = SUM(errores) / SUM(líneas)
--   Cumplimiento de meta  = SUM(líneas) / SUM(horas x meta de la zona)
-- Importante: no se promedian los ratios diarios; un día de 3 horas pesaría
-- igual que uno de 8 y sesgaría el resultado.
-- ============================================================

DROP TABLE IF EXISTS picking_valido;
CREATE TABLE picking_valido AS
SELECT p.id_registro, p.fecha,
       date(p.fecha, '-6 days', 'weekday 1')                       AS semana_inicio,   -- lunes de la semana
       substr(p.fecha, 1, 7)                                       AS mes,
       CASE WHEN p.fecha < '2026-07-01' THEN 'Antes (abr-jun)' ELSE 'Después (jul-sep)' END AS periodo,
       CAST(strftime('%w', p.fecha) AS INTEGER)                    AS dia_num,
       p.id_operador, p.turno, p.zona,
       p.lineas, p.unidades, p.horas, p.errores,
       ROUND(p.lineas / p.horas, 2)                                AS lph,
       m.meta_lineas_hora                                          AS meta_lph,
       CASE WHEN p.lineas / p.horas >= m.meta_lineas_hora THEN 1 ELSE 0 END AS sobre_meta,
       p.horas * m.meta_lineas_hora                                AS lineas_esperadas,
       o.antiguedad_meses_inicio
         + (CAST(strftime('%Y', p.fecha) AS INTEGER) - 2026) * 12
         + CAST(strftime('%m', p.fecha) AS INTEGER) - 4            AS antiguedad_meses
FROM picking_limpio p
JOIN metas m USING (zona)
JOIN operadores o USING (id_operador)
WHERE p.estado = 'VALIDO';

DROP TABLE IF EXISTS kpi_global;
CREATE TABLE kpi_global AS
SELECT COUNT(*)                                                    AS registros,
       SUM(lineas)                                                 AS lineas,
       ROUND(SUM(horas), 1)                                        AS horas,
       ROUND(SUM(lineas) / SUM(horas), 1)                          AS lph,
       ROUND(SUM(unidades) / SUM(horas), 1)                        AS uph,
       ROUND(100.0 * SUM(errores) / SUM(lineas), 2)                AS error_pct,
       ROUND(100.0 * SUM(lineas) / SUM(lineas_esperadas), 1)       AS cumplimiento_meta_pct,
       ROUND(100.0 * AVG(sobre_meta), 1)                           AS pct_registros_sobre_meta
FROM picking_valido;

-- Plantilla repetida por cada corte de análisis
DROP TABLE IF EXISTS kpi_mensual;
CREATE TABLE kpi_mensual AS
SELECT mes,
       ROUND(SUM(lineas) / SUM(horas), 1)                          AS lph,
       ROUND(100.0 * SUM(errores) / SUM(lineas), 2)                AS error_pct,
       ROUND(100.0 * SUM(lineas) / SUM(lineas_esperadas), 1)       AS cumplimiento_meta_pct,
       SUM(lineas) AS lineas, ROUND(SUM(horas), 1) AS horas
FROM picking_valido GROUP BY mes ORDER BY mes;

DROP TABLE IF EXISTS kpi_semanal;
CREATE TABLE kpi_semanal AS
SELECT semana_inicio,
       ROUND(SUM(lineas) / SUM(horas), 1)                          AS lph,
       ROUND(100.0 * SUM(errores) / SUM(lineas), 2)                AS error_pct,
       ROUND(100.0 * SUM(lineas) / SUM(lineas_esperadas), 1)       AS cumplimiento_meta_pct
FROM picking_valido GROUP BY semana_inicio ORDER BY semana_inicio;

DROP TABLE IF EXISTS kpi_periodo;
CREATE TABLE kpi_periodo AS
SELECT periodo,
       ROUND(SUM(lineas) / SUM(horas), 1)                          AS lph,
       ROUND(100.0 * SUM(errores) / SUM(lineas), 2)                AS error_pct,
       ROUND(100.0 * SUM(lineas) / SUM(lineas_esperadas), 1)       AS cumplimiento_meta_pct
FROM picking_valido GROUP BY periodo ORDER BY MIN(fecha);

DROP TABLE IF EXISTS kpi_turno;
CREATE TABLE kpi_turno AS
SELECT turno,
       ROUND(SUM(lineas) / SUM(horas), 1)                          AS lph,
       ROUND(100.0 * SUM(errores) / SUM(lineas), 2)                AS error_pct,
       ROUND(100.0 * SUM(lineas) / SUM(lineas_esperadas), 1)       AS cumplimiento_meta_pct
FROM picking_valido GROUP BY turno
ORDER BY CASE turno WHEN 'Mañana' THEN 1 WHEN 'Tarde' THEN 2 ELSE 3 END;

DROP TABLE IF EXISTS kpi_zona;
CREATE TABLE kpi_zona AS
SELECT zona, MAX(meta_lph)                                         AS meta_lph,
       ROUND(SUM(lineas) / SUM(horas), 1)                          AS lph,
       ROUND(100.0 * SUM(errores) / SUM(lineas), 2)                AS error_pct,
       ROUND(100.0 * SUM(lineas) / SUM(lineas_esperadas), 1)       AS cumplimiento_meta_pct
FROM picking_valido GROUP BY zona ORDER BY cumplimiento_meta_pct DESC;

DROP TABLE IF EXISTS kpi_dia;
CREATE TABLE kpi_dia AS
SELECT CASE dia_num WHEN 1 THEN 'Lun' WHEN 2 THEN 'Mar' WHEN 3 THEN 'Mié'
                    WHEN 4 THEN 'Jue' WHEN 5 THEN 'Vie' ELSE 'Sáb' END AS dia,
       dia_num,
       ROUND(100.0 * SUM(lineas) / SUM(lineas_esperadas), 1)       AS cumplimiento_meta_pct,
       ROUND(100.0 * SUM(errores) / SUM(lineas), 2)                AS error_pct
FROM picking_valido GROUP BY dia_num ORDER BY dia_num;

DROP TABLE IF EXISTS kpi_antiguedad;
CREATE TABLE kpi_antiguedad AS
SELECT CASE WHEN antiguedad_meses < 6  THEN '1. Menos de 6 meses'
            WHEN antiguedad_meses < 18 THEN '2. 6 a 17 meses'
            ELSE '3. 18 meses o más' END                           AS banda_antiguedad,
       COUNT(*)                                                    AS registros,
       ROUND(100.0 * SUM(lineas) / SUM(lineas_esperadas), 1)       AS cumplimiento_meta_pct,
       ROUND(100.0 * SUM(errores) / SUM(lineas), 2)                AS error_pct
FROM picking_valido GROUP BY 1 ORDER BY 1;

DROP TABLE IF EXISTS kpi_operador;
CREATE TABLE kpi_operador AS
SELECT id_operador, o.turno_asignado AS turno, o.zona_principal,
       COUNT(*)                                                    AS dias,
       ROUND(SUM(lineas) / SUM(horas), 1)                          AS lph,
       ROUND(100.0 * SUM(lineas) / SUM(lineas_esperadas), 1)       AS cumplimiento_meta_pct,
       ROUND(100.0 * SUM(errores) / SUM(lineas), 2)                AS error_pct,
       ROUND(100.0 * AVG(sobre_meta), 1)                           AS pct_dias_sobre_meta,
       RANK() OVER (ORDER BY SUM(lineas) / SUM(lineas_esperadas) DESC) AS ranking
FROM picking_valido
JOIN operadores o USING (id_operador)
GROUP BY id_operador
ORDER BY ranking;
