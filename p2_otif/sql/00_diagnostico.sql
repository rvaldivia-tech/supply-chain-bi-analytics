-- ============================================================
-- PROYECTO 2 · NIVEL DE SERVICIO OTIF
-- 00_diagnostico.sql
-- Tablas crudas: despachos_raw, clientes_raw
-- ============================================================

DROP TABLE IF EXISTS calidad_datos;
CREATE TABLE calidad_datos (problema TEXT, filas INTEGER, tratamiento TEXT);

INSERT INTO calidad_datos
SELECT 'Filas totales en bruto', COUNT(*), 'Referencia' FROM despachos_raw;

INSERT INTO calidad_datos
SELECT 'id_pedido duplicado (filas sobrantes)', COUNT(*) - COUNT(DISTINCT id_pedido),
       'Se conserva la primera aparición'
FROM despachos_raw;

INSERT INTO calidad_datos
SELECT 'Fechas en formato dd/mm/yyyy (pedido, compromiso o entrega)', COUNT(*),
       'Se convierten a yyyy-mm-dd'
FROM despachos_raw
WHERE fecha_pedido LIKE '__/__/____' OR fecha_compromiso LIKE '__/__/____' OR fecha_entrega LIKE '__/__/____';

INSERT INTO calidad_datos
SELECT 'Transportista con nombre inconsistente', COUNT(*),
       'Se unifica a 4 transportistas (TRIM, mayúsculas, espacios)'
FROM despachos_raw
WHERE transportista NOT IN ('Flota propia', 'RapidoLima', 'LogiSur', 'TransAndes');

INSERT INTO calidad_datos
SELECT 'Pedidos sin fecha de entrega (pendientes al corte)', COUNT(*),
       'Se excluyen del OTIF: aún no se pueden evaluar'
FROM despachos_raw
WHERE fecha_entrega IS NULL OR TRIM(fecha_entrega) = '';

INSERT INTO calidad_datos
SELECT 'Cantidad entregada vacía (con entrega registrada)', COUNT(*),
       'Se excluyen: no se puede evaluar In Full'
FROM despachos_raw
WHERE (cant_entregada IS NULL OR TRIM(cant_entregada) = '')
  AND fecha_entrega IS NOT NULL AND TRIM(fecha_entrega) <> '';

INSERT INTO calidad_datos
SELECT 'Sobreentrega (entregado > pedido)', COUNT(*),
       'Se mantiene como completo; en fill rate se limita a lo pedido'
FROM despachos_raw
WHERE CAST(NULLIF(TRIM(cant_entregada), '') AS INTEGER) > CAST(cant_pedida AS INTEGER);
