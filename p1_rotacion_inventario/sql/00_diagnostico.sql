-- ============================================================
-- PROYECTO 1 · ROTACIÓN DE INVENTARIO
-- 00_diagnostico.sql
-- Objetivo: medir los problemas de calidad ANTES de corregir nada.
-- Tablas de entrada (texto crudo): movimientos_raw, productos_raw
-- ============================================================

DROP TABLE IF EXISTS calidad_datos;
CREATE TABLE calidad_datos (problema TEXT, filas INTEGER, tratamiento TEXT);

-- 1) Filas totales
INSERT INTO calidad_datos
SELECT 'Filas totales en bruto', COUNT(*), 'Referencia' FROM movimientos_raw;

-- 2) Duplicados exactos por id_mov
INSERT INTO calidad_datos
SELECT 'id_mov duplicado (filas sobrantes)',
       COUNT(*) - COUNT(DISTINCT id_mov),
       'Se conserva la primera aparición'
FROM movimientos_raw;

-- 3) Cantidades nulas o vacías
INSERT INTO calidad_datos
SELECT 'Cantidad nula o vacía', COUNT(*),
       'Se excluye: no se puede inferir la cantidad'
FROM movimientos_raw
WHERE cantidad IS NULL OR TRIM(cantidad) = '';

-- 4) Cantidades negativas
INSERT INTO calidad_datos
SELECT 'Cantidad negativa', COUNT(*),
       'Se toma el valor absoluto (error de signo; el tipo ya indica ENTRADA/SALIDA)'
FROM movimientos_raw
WHERE CAST(cantidad AS INTEGER) < 0;

-- 5) Fechas en formato dd/mm/yyyy
INSERT INTO calidad_datos
SELECT 'Fecha en formato dd/mm/yyyy', COUNT(*),
       'Se convierte a yyyy-mm-dd'
FROM movimientos_raw
WHERE fecha LIKE '__/__/____';

-- 6) SKU con espacios o minúsculas
INSERT INTO calidad_datos
SELECT 'SKU con espacios o minúsculas', COUNT(*),
       'TRIM + UPPER'
FROM movimientos_raw
WHERE sku <> UPPER(TRIM(sku));

-- 7) SKU que no existen en el maestro (después de normalizar)
INSERT INTO calidad_datos
SELECT 'SKU sin match en maestro', COUNT(*),
       'Se excluiría (0 esperado)'
FROM movimientos_raw m
WHERE UPPER(TRIM(m.sku)) NOT IN (SELECT sku FROM productos_raw);
