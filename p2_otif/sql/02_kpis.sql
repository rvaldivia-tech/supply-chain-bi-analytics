-- ============================================================
-- 02_kpis.sql
-- Definiciones (nivel pedido):
--   A tiempo (On Time) = fecha_entrega <= fecha_compromiso
--   Completo (In Full) = cant_entregada >= cant_pedida
--   OTIF               = A tiempo Y Completo
--   Fill rate          = SUM(MIN(entregado, pedido)) / SUM(pedido)   (nivel unidades)
-- El mes se asigna por fecha de compromiso.
-- ============================================================

DROP TABLE IF EXISTS otif_pedidos;
CREATE TABLE otif_pedidos AS
SELECT d.id_pedido,
       substr(d.fecha_compromiso, 1, 7)                                    AS mes,
       d.fecha_pedido, d.fecha_compromiso, d.fecha_entrega,
       d.id_cliente, c.cliente, c.canal, c.zona, d.transportista,
       d.cant_pedida, d.cant_entregada,
       CASE WHEN d.cant_entregada < d.cant_pedida THEN d.cant_entregada ELSE d.cant_pedida END AS unidades_cumplidas,
       CASE WHEN d.fecha_entrega <= d.fecha_compromiso THEN 1 ELSE 0 END   AS a_tiempo,
       CASE WHEN d.cant_entregada >= d.cant_pedida     THEN 1 ELSE 0 END   AS completo,
       CASE WHEN d.fecha_entrega <= d.fecha_compromiso
             AND d.cant_entregada >= d.cant_pedida     THEN 1 ELSE 0 END   AS otif,
       MAX(0, CAST(julianday(d.fecha_entrega) - julianday(d.fecha_compromiso) AS INTEGER)) AS dias_retraso,
       CAST(julianday(d.fecha_entrega) - julianday(d.fecha_pedido) AS INTEGER)             AS lead_time_real,
       d.motivo_falla
FROM despachos_limpio d
JOIN clientes c USING (id_cliente)
WHERE d.estado = 'EVALUABLE'
  AND d.fecha_compromiso <= '2026-09-30';   -- solo compromisos dentro del periodo analizado

-- Macro de KPIs reutilizada en cada corte
DROP TABLE IF EXISTS kpi_mensual;
CREATE TABLE kpi_mensual AS
SELECT mes,
       COUNT(*)                                          AS pedidos,
       ROUND(100.0 * AVG(a_tiempo), 1)                   AS pct_a_tiempo,
       ROUND(100.0 * AVG(completo), 1)                   AS pct_completo,
       ROUND(100.0 * AVG(otif), 1)                       AS pct_otif,
       ROUND(100.0 * SUM(unidades_cumplidas) / SUM(cant_pedida), 1) AS fill_rate,
       ROUND(AVG(lead_time_real), 2)                     AS lead_time_prom
FROM otif_pedidos
GROUP BY mes
ORDER BY mes;

DROP TABLE IF EXISTS kpi_transportista;
CREATE TABLE kpi_transportista AS
SELECT transportista,
       COUNT(*)                                          AS pedidos,
       ROUND(100.0 * AVG(a_tiempo), 1)                   AS pct_a_tiempo,
       ROUND(100.0 * AVG(completo), 1)                   AS pct_completo,
       ROUND(100.0 * AVG(otif), 1)                       AS pct_otif,
       ROUND(AVG(CASE WHEN a_tiempo = 0 THEN dias_retraso END), 2) AS retraso_prom_dias
FROM otif_pedidos
GROUP BY transportista
ORDER BY pct_otif DESC;

DROP TABLE IF EXISTS kpi_canal;
CREATE TABLE kpi_canal AS
SELECT canal,
       COUNT(*)                                          AS pedidos,
       ROUND(100.0 * AVG(a_tiempo), 1)                   AS pct_a_tiempo,
       ROUND(100.0 * AVG(completo), 1)                   AS pct_completo,
       ROUND(100.0 * AVG(otif), 1)                       AS pct_otif
FROM otif_pedidos
GROUP BY canal
ORDER BY pct_otif DESC;

DROP TABLE IF EXISTS kpi_zona;
CREATE TABLE kpi_zona AS
SELECT zona,
       COUNT(*)                                          AS pedidos,
       ROUND(100.0 * AVG(a_tiempo), 1)                   AS pct_a_tiempo,
       ROUND(100.0 * AVG(completo), 1)                   AS pct_completo,
       ROUND(100.0 * AVG(otif), 1)                       AS pct_otif
FROM otif_pedidos
GROUP BY zona
ORDER BY pct_otif DESC;

DROP TABLE IF EXISTS kpi_cliente;
CREATE TABLE kpi_cliente AS
SELECT id_cliente, cliente, canal, zona,
       COUNT(*)                                          AS pedidos,
       ROUND(100.0 * AVG(otif), 1)                       AS pct_otif
FROM otif_pedidos
GROUP BY id_cliente
ORDER BY pct_otif;

-- Pareto de causas de falla (pedidos que no fueron OTIF)
DROP TABLE IF EXISTS kpi_motivo;
CREATE TABLE kpi_motivo AS
WITH f AS (
    SELECT COALESCE(motivo_falla, 'Sin motivo registrado') AS motivo, COUNT(*) AS pedidos_fallidos
    FROM otif_pedidos WHERE otif = 0 GROUP BY 1
)
SELECT motivo,
       pedidos_fallidos,
       ROUND(100.0 * pedidos_fallidos / SUM(pedidos_fallidos) OVER (), 1) AS pct,
       ROUND(100.0 * SUM(pedidos_fallidos) OVER (ORDER BY pedidos_fallidos DESC, motivo
             ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) / SUM(pedidos_fallidos) OVER (), 1) AS pct_acumulado
FROM f
ORDER BY pedidos_fallidos DESC;

DROP TABLE IF EXISTS kpi_global;
CREATE TABLE kpi_global AS
SELECT COUNT(*)                                          AS pedidos_evaluados,
       ROUND(100.0 * AVG(a_tiempo), 1)                   AS pct_a_tiempo,
       ROUND(100.0 * AVG(completo), 1)                   AS pct_completo,
       ROUND(100.0 * AVG(otif), 1)                       AS pct_otif,
       ROUND(100.0 * SUM(unidades_cumplidas) / SUM(cant_pedida), 1) AS fill_rate,
       ROUND(AVG(lead_time_real), 2)                     AS lead_time_prom
FROM otif_pedidos;
