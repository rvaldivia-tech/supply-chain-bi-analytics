# Proyecto 2 · Nivel de servicio OTIF

> Datos **simulados** (no provienen de ninguna empresa). Se generaron con errores de calidad a propósito.

## Pregunta de negocio
¿Qué porcentaje de pedidos llega a tiempo y completo, y dónde y por qué se pierde el servicio?

## Datos
| Archivo | Contenido |
|---|---|
| `data/despachos.csv` | Pedidos con fecha de pedido, compromiso y entrega, cantidades, transportista y motivo de falla (oct 2025 – sep 2026) |
| `data/clientes.csv` | 40 clientes con canal y zona |

## Limpieza (`sql/00_diagnostico.sql` y `sql/01_limpieza.sql`)
| Problema | Filas | Tratamiento |
|---|---|---|
| Filas totales en bruto | 5853 | Referencia |
| id_pedido duplicado (filas sobrantes) | 30 | Se conserva la primera aparición |
| Fechas en formato dd/mm/yyyy (pedido, compromiso o entrega) | 151 | Se convierten a yyyy-mm-dd |
| Transportista con nombre inconsistente | 92 | Se unifica a 4 transportistas (TRIM, mayúsculas, espacios) |
| Pedidos sin fecha de entrega (pendientes al corte) | 55 | Se excluyen del OTIF: aún no se pueden evaluar |
| Cantidad entregada vacía (con entrega registrada) | 20 | Se excluyen: no se puede evaluar In Full |
| Sobreentrega (entregado > pedido) | 25 | Se mantiene como completo; en fill rate se limita a lo pedido |
| Entrega anterior al pedido (fechas invertidas) | 12 | Se excluyen: no se sabe cuál fecha es la correcta |
| Pedidos evaluables para OTIF | 5736 | Base de los KPIs |

## Métricas (`sql/02_kpis.sql`)
- **A tiempo** = fecha de entrega ≤ fecha compromiso. **Completo** = cantidad entregada ≥ pedida. **OTIF** = ambas a la vez, por pedido.
- **Fill rate** = suma de min(entregado, pedido) ÷ suma de pedido (unidades).
- El mes se asigna por fecha compromiso y solo se evalúan compromisos dentro del periodo.
- **Pareto de causas** con porcentaje acumulado calculado con funciones de ventana.

## Resultados
- OTIF global **77.4%** (a tiempo 87.1%, completo 88.9%, fill rate 96.9%) sobre 5,735 pedidos.
- Tendencia: de **71.5%** en 2025-10 a **82.6%** en 2026-09.
- Transportistas: Flota propia 84.5% frente a LogiSur 65.8%. La brecha viene de la puntualidad.
- Zona más débil: **Provincia** con 61.3% de OTIF.
- Las dos primeras causas (Quiebre de stock y Retraso de transporte) explican el 51% de los pedidos fallidos.

## Cómo reproducirlo
```bash
python3 generar_datos.py
python3 run.py
```

## Power BI
Importa de `output/`: `otif_pedidos.csv` (tabla de hechos, una fila por pedido evaluado), `kpi_motivo.csv` y, si quieres modelar, `clientes.csv`.

```dax
Pedidos = COUNTROWS ( otif_pedidos )
% A Tiempo = DIVIDE ( SUM ( otif_pedidos[a_tiempo] ), [Pedidos] )
% Completo = DIVIDE ( SUM ( otif_pedidos[completo] ), [Pedidos] )
% OTIF = DIVIDE ( SUM ( otif_pedidos[otif] ), [Pedidos] )
Fill Rate = DIVIDE ( SUM ( otif_pedidos[unidades_cumplidas] ), SUM ( otif_pedidos[cant_pedida] ) )
Retraso Promedio (días) = AVERAGEX ( FILTER ( otif_pedidos, otif_pedidos[a_tiempo] = 0 ), otif_pedidos[dias_retraso] )
```
Visuales sugeridos: tarjetas, líneas de % OTIF, % a tiempo y % completo por mes, barras por transportista y zona, y Pareto de causas. Segmentadores: canal, zona y transportista.

## Limitaciones
- Los pedidos de las últimas semanas con entrega pendiente quedan fuera, lo que puede favorecer levemente al último mes.
- El motivo de falla registra una sola causa por pedido, aunque un pedido puede fallar por dos.
