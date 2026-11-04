-- ============================================================
-- 02_kpis.sql
-- Rotación, días de inventario y clasificación ABC por SKU.
--
-- Definiciones:
--   Costo de salidas (COGS)   = unidades SALIDA x costo_unitario
--   Inventario promedio ($)   = promedio de los 12 cierres mensuales x costo_unitario
--   Rotación                  = COGS anual / inventario promedio ($)
--   Días de inventario        = 365 / rotación
-- ============================================================

-- 1) Calendario de meses presentes en los datos
DROP TABLE IF EXISTS meses;
CREATE TABLE meses AS
SELECT DISTINCT substr(fecha, 1, 7) AS mes FROM mov_limpio;

-- 2) Entradas y salidas por SKU y mes (con malla completa SKU x mes)
DROP TABLE IF EXISTS neto_mensual;
CREATE TABLE neto_mensual AS
SELECT p.sku,
       m.mes,
       COALESCE(SUM(CASE WHEN l.tipo = 'ENTRADA' THEN l.cantidad END), 0) AS entradas,
       COALESCE(SUM(CASE WHEN l.tipo = 'SALIDA'  THEN l.cantidad END), 0) AS salidas
FROM productos p
CROSS JOIN meses m
LEFT JOIN mov_limpio l
       ON l.sku = p.sku AND substr(l.fecha, 1, 7) = m.mes
GROUP BY p.sku, m.mes;

-- 3) Stock de cierre mensual = stock inicial + acumulado (entradas - salidas)
DROP TABLE IF EXISTS stock_mensual;
CREATE TABLE stock_mensual AS
SELECT n.sku,
       n.mes,
       n.entradas,
       n.salidas,
       p.stock_inicial
         + SUM(n.entradas - n.salidas) OVER (
               PARTITION BY n.sku ORDER BY n.mes
               ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS stock_cierre,
       p.costo_unitario
FROM neto_mensual n
JOIN productos p USING (sku);

-- 4) KPIs por SKU
DROP TABLE IF EXISTS kpi_sku_base;
CREATE TABLE kpi_sku_base AS
SELECT p.sku,
       p.descripcion,
       p.categoria,
       p.costo_unitario,
       p.stock_inicial,
       SUM(s.salidas)                                  AS unidades_salida,
       SUM(s.entradas)                                 AS unidades_entrada,
       SUM(s.salidas) * p.costo_unitario               AS cogs,
       AVG(s.stock_cierre)                             AS stock_prom_unid,
       AVG(s.stock_cierre) * p.costo_unitario          AS inv_prom_valor,
       MIN(s.stock_cierre)                             AS stock_minimo,
       SUM(CASE WHEN s.stock_cierre < 0 THEN 1 ELSE 0 END) AS meses_stock_negativo
FROM productos p
JOIN stock_mensual s USING (sku)
GROUP BY p.sku;

-- 5) Rotación, días y ABC
DROP TABLE IF EXISTS kpi_sku;
CREATE TABLE kpi_sku AS
WITH acum AS (
    SELECT *,
           SUM(cogs) OVER ()                                   AS cogs_total,
           SUM(cogs) OVER (ORDER BY cogs DESC, sku
                           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cogs_acum
    FROM kpi_sku_base
)
SELECT sku, descripcion, categoria, costo_unitario, stock_inicial,
       unidades_entrada, unidades_salida,
       ROUND(cogs, 2)                                           AS cogs,
       ROUND(inv_prom_valor, 2)                                 AS inv_prom_valor,
       CASE WHEN inv_prom_valor > 0 THEN ROUND(cogs / inv_prom_valor, 2) END AS rotacion,
       CASE WHEN cogs > 0 AND inv_prom_valor > 0
            THEN ROUND(365.0 * inv_prom_valor / cogs, 0) END    AS dias_inventario,
       CASE WHEN (cogs_acum - cogs) / cogs_total < 0.80 THEN 'A'
            WHEN (cogs_acum - cogs) / cogs_total < 0.95 THEN 'B'
            ELSE 'C' END                                        AS clase_abc,
       ROUND(100.0 * cogs / cogs_total, 2)                      AS pct_cogs,
       stock_minimo,
       meses_stock_negativo
FROM acum;

-- 6) Segmentación de salud del inventario
DROP TABLE IF EXISTS kpi_sku_final;
CREATE TABLE kpi_sku_final AS
SELECT *,
       CASE WHEN meses_stock_negativo > 0 THEN 'Revisar: stock negativo'
            WHEN dias_inventario IS NULL   THEN 'Sin dato'
            WHEN dias_inventario > 180     THEN 'Exceso (> 180 días)'
            WHEN dias_inventario > 90      THEN 'Alto (91-180 días)'
            WHEN dias_inventario >= 30     THEN 'Saludable (30-90 días)'
            ELSE 'Riesgo de quiebre (< 30 días)' END           AS estado_inventario
FROM kpi_sku;
DROP TABLE kpi_sku;
ALTER TABLE kpi_sku_final RENAME TO kpi_sku;

-- 7) KPI por categoría
DROP TABLE IF EXISTS kpi_categoria;
CREATE TABLE kpi_categoria AS
SELECT categoria,
       COUNT(*)                                       AS skus,
       ROUND(SUM(cogs), 2)                            AS cogs,
       ROUND(SUM(inv_prom_valor), 2)                  AS inv_prom_valor,
       ROUND(SUM(cogs) / SUM(inv_prom_valor), 2)      AS rotacion,
       ROUND(365.0 * SUM(inv_prom_valor) / SUM(cogs), 0) AS dias_inventario
FROM kpi_sku
GROUP BY categoria
ORDER BY cogs DESC;

-- 8) Serie mensual: valor del inventario al cierre y costo de salidas
DROP TABLE IF EXISTS kpi_mensual;
CREATE TABLE kpi_mensual AS
SELECT mes,
       ROUND(SUM(salidas * costo_unitario), 2)        AS cogs,
       ROUND(SUM(stock_cierre * costo_unitario), 2)   AS inventario_cierre_valor
FROM stock_mensual
GROUP BY mes
ORDER BY mes;

-- 9) KPI global
DROP TABLE IF EXISTS kpi_global;
CREATE TABLE kpi_global AS
SELECT ROUND(SUM(cogs), 2)                            AS cogs_anual,
       ROUND(SUM(inv_prom_valor), 2)                  AS inv_prom_valor,
       ROUND(SUM(cogs) / SUM(inv_prom_valor), 2)      AS rotacion_global,
       ROUND(365.0 * SUM(inv_prom_valor) / SUM(cogs), 0) AS dias_inventario_global,
       COUNT(*)                                       AS skus
FROM kpi_sku;
