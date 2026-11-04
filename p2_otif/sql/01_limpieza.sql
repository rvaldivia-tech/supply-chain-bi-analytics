-- ============================================================
-- 01_limpieza.sql
-- despachos_limpio: todas las filas únicas, normalizadas y con un estado.
-- Solo las filas con estado 'EVALUABLE' entran al cálculo del OTIF.
-- ============================================================

DROP TABLE IF EXISTS clientes;
CREATE TABLE clientes AS SELECT * FROM clientes_raw;

DROP TABLE IF EXISTS despachos_limpio;
CREATE TABLE despachos_limpio AS
WITH normalizado AS (
    SELECT
        id_pedido,
        CASE WHEN fecha_pedido LIKE '__/__/____'
             THEN substr(fecha_pedido,7,4)||'-'||substr(fecha_pedido,4,2)||'-'||substr(fecha_pedido,1,2)
             ELSE fecha_pedido END                                        AS fecha_pedido,
        CASE WHEN fecha_compromiso LIKE '__/__/____'
             THEN substr(fecha_compromiso,7,4)||'-'||substr(fecha_compromiso,4,2)||'-'||substr(fecha_compromiso,1,2)
             ELSE fecha_compromiso END                                    AS fecha_compromiso,
        CASE WHEN fecha_entrega LIKE '__/__/____'
             THEN substr(fecha_entrega,7,4)||'-'||substr(fecha_entrega,4,2)||'-'||substr(fecha_entrega,1,2)
             ELSE NULLIF(TRIM(fecha_entrega), '') END                     AS fecha_entrega,
        id_cliente,
        CASE UPPER(REPLACE(TRIM(transportista), ' ', ''))
             WHEN 'FLOTAPROPIA' THEN 'Flota propia'
             WHEN 'RAPIDOLIMA'  THEN 'RapidoLima'
             WHEN 'LOGISUR'     THEN 'LogiSur'
             WHEN 'TRANSANDES'  THEN 'TransAndes'
             ELSE 'Otro' END                                              AS transportista,
        CAST(cant_pedida AS INTEGER)                                      AS cant_pedida,
        CAST(NULLIF(TRIM(cant_entregada), '') AS INTEGER)                 AS cant_entregada,
        NULLIF(TRIM(motivo_falla), '')                                    AS motivo_falla,
        ROW_NUMBER() OVER (PARTITION BY id_pedido ORDER BY rowid)         AS rn
    FROM despachos_raw
)
SELECT id_pedido, fecha_pedido, fecha_compromiso, fecha_entrega, id_cliente, transportista,
       cant_pedida, cant_entregada, motivo_falla,
       CASE WHEN fecha_entrega IS NULL                   THEN 'PENDIENTE'
            WHEN fecha_entrega < fecha_pedido            THEN 'FECHAS_INCONSISTENTES'
            WHEN cant_entregada IS NULL                  THEN 'SIN_CANTIDAD'
            ELSE 'EVALUABLE' END                                          AS estado
FROM normalizado
WHERE rn = 1;

INSERT INTO calidad_datos
SELECT 'Entrega anterior al pedido (fechas invertidas)', COUNT(*),
       'Se excluyen: no se sabe cuál fecha es la correcta'
FROM despachos_limpio WHERE estado = 'FECHAS_INCONSISTENTES';

INSERT INTO calidad_datos
SELECT 'Pedidos evaluables para OTIF', COUNT(*), 'Base de los KPIs'
FROM despachos_limpio WHERE estado = 'EVALUABLE';
