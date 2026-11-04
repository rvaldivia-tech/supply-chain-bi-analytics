-- ============================================================
-- 01_limpieza.sql
-- Construye mov_limpio y productos aplicando las reglas del diagnóstico.
-- ============================================================

DROP TABLE IF EXISTS productos;
CREATE TABLE productos AS
SELECT sku,
       descripcion,
       categoria,
       CAST(costo_unitario AS REAL) AS costo_unitario,
       CAST(stock_inicial  AS INTEGER) AS stock_inicial
FROM productos_raw;

DROP TABLE IF EXISTS mov_limpio;
CREATE TABLE mov_limpio AS
WITH normalizado AS (
    SELECT
        CAST(id_mov AS INTEGER)                                  AS id_mov,
        CASE WHEN fecha LIKE '__/__/____'
             THEN substr(fecha, 7, 4) || '-' || substr(fecha, 4, 2) || '-' || substr(fecha, 1, 2)
             ELSE fecha END                                      AS fecha,
        UPPER(TRIM(sku))                                         AS sku,
        UPPER(TRIM(tipo))                                        AS tipo,
        CASE WHEN cantidad IS NULL OR TRIM(cantidad) = ''
             THEN NULL
             ELSE ABS(CAST(cantidad AS INTEGER)) END             AS cantidad,
        almacen,
        ROW_NUMBER() OVER (PARTITION BY id_mov ORDER BY rowid)   AS rn
    FROM movimientos_raw
)
SELECT id_mov, fecha, sku, tipo, cantidad, almacen
FROM normalizado
WHERE rn = 1              -- elimina duplicados
  AND cantidad IS NOT NULL; -- elimina cantidades nulas

-- Control: filas finales
INSERT INTO calidad_datos
SELECT 'Filas finales en mov_limpio', COUNT(*), 'Base para los KPIs' FROM mov_limpio;
