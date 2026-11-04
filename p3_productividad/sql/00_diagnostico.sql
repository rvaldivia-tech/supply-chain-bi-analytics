-- ============================================================
-- PROYECTO 3 · PRODUCTIVIDAD DE ALMACÉN (PICKING)
-- 00_diagnostico.sql
-- Tablas crudas: picking_raw, operadores_raw, metas_raw
-- ============================================================

DROP TABLE IF EXISTS calidad_datos;
CREATE TABLE calidad_datos (problema TEXT, filas INTEGER, tratamiento TEXT);

INSERT INTO calidad_datos
SELECT 'Filas totales en bruto', COUNT(*), 'Referencia' FROM picking_raw;

INSERT INTO calidad_datos
SELECT 'id_registro duplicado (filas sobrantes)', COUNT(*) - COUNT(DISTINCT id_registro),
       'Se conserva la primera aparición'
FROM picking_raw;

INSERT INTO calidad_datos
SELECT 'Fecha en formato dd/mm/yyyy', COUNT(*), 'Se convierte a yyyy-mm-dd'
FROM picking_raw WHERE fecha LIKE '__/__/____';

INSERT INTO calidad_datos
SELECT 'Turno escrito de forma inconsistente', COUNT(*),
       'Se unifica a Mañana / Tarde / Noche'
FROM picking_raw WHERE turno NOT IN ('Mañana', 'Tarde', 'Noche');

INSERT INTO calidad_datos
SELECT 'Horas vacías o en cero', COUNT(*), 'Se excluyen: no se puede calcular líneas por hora'
FROM picking_raw WHERE horas IS NULL OR TRIM(horas) = '' OR CAST(horas AS REAL) = 0;

INSERT INTO calidad_datos
SELECT 'Horas atípicas (> 12 en un día)', COUNT(*),
       'Se excluyen: error de digitación probable (72 en lugar de 7.2)'
FROM picking_raw WHERE CAST(NULLIF(TRIM(horas), '') AS REAL) > 12;

INSERT INTO calidad_datos
SELECT 'Líneas vacías', COUNT(*), 'Se excluyen'
FROM picking_raw WHERE lineas IS NULL OR TRIM(lineas) = '';

INSERT INTO calidad_datos
SELECT 'Líneas negativas', COUNT(*),
       'Se excluyen: podría ser una reversa y no un picking'
FROM picking_raw WHERE CAST(NULLIF(TRIM(lineas), '') AS INTEGER) < 0;
