import os, pandas as pd
R = os.path.dirname(os.path.abspath(__file__))
rd = lambda p, t: pd.read_csv(f"{R}/{p}/output/{t}.csv")
def md(df): return "| " + " | ".join(df.columns) + " |\n|" + "---|" * len(df.columns) + "\n" + "\n".join("| " + " | ".join(str(x) for x in r) + " |" for r in df.values)
def calidad(p):
    c = rd(p, "calidad_datos"); c.columns = ["Problema", "Filas", "Tratamiento"]; return md(c)

# ---------------- P1 ----------------
p = "p1_rotacion_inventario"; g = rd(p, "kpi_global").iloc[0]; sku = rd(p, "kpi_sku"); cat = rd(p, "kpi_categoria")
tot = sku.cogs.sum(); A = sku[sku.clase_abc == "A"]
alto = sku[sku.dias_inventario > 90]
open(f"{R}/{p}/README.md", "w", encoding="utf-8").write(f"""# Proyecto 1 · Rotación de inventario

> Datos **simulados** (no provienen de ninguna empresa). Se generaron con errores de calidad a propósito para practicar limpieza.

## Pregunta de negocio
¿Cuántas veces rota el inventario, cuántos días de cobertura hay y qué SKUs inmovilizan capital o están cerca del quiebre?

## Datos
| Archivo | Contenido |
|---|---|
| `data/productos.csv` | 60 SKUs: categoría, costo unitario, stock inicial |
| `data/movimientos.csv` | Entradas y salidas de 12 meses (oct 2025 – sep 2026) en 2 almacenes |

## Limpieza (SQL, `sql/00_diagnostico.sql` y `sql/01_limpieza.sql`)
Primero se mide cada problema y después se corrige.

{calidad(p)}

## Métricas (`sql/02_kpis.sql`)
- **Costo de salidas** = unidades de salida × costo unitario.
- **Inventario promedio** = promedio de los 12 stocks de cierre mensual × costo. Stock de cierre = stock inicial + acumulado (entradas − salidas), calculado con una función de ventana.
- **Rotación** = costo de salidas anual ÷ inventario promedio. **Días de inventario** = 365 ÷ rotación.
- **ABC** por costo de salidas acumulado: A hasta 80%, B hasta 95%, C el resto.
- **Estado**: riesgo de quiebre (< 30 días), saludable (30 a 90), alto (91 a 180), exceso (> 180) y revisar (stock negativo en algún cierre).

## Resultados
- Rotación global de **{g.cogs_anual / g.inv_prom_valor:.1f}×**, equivalente a **{g.dias_inventario_global:.0f} días** de inventario. Costo de salidas S/ {g.cogs_anual:,.0f} e inventario promedio S/ {g.inv_prom_valor:,.0f}.
- Los **{len(A)} SKUs clase A** concentran el {100*A.cogs.sum()/tot:.0f}% del costo de salidas.
- **{len(alto)} SKUs superan 90 días** de cobertura y mantienen S/ {alto.inv_prom_valor.sum():,.0f} en inventario promedio ({100*alto.inv_prom_valor.sum()/g.inv_prom_valor:.0f}% del total).
- Categoría con rotación más lenta: **{cat.sort_values('dias_inventario').iloc[-1].categoria}** ({cat.dias_inventario.max():.0f} días).
- {int((sku.meses_stock_negativo > 0).sum())} SKU con stock negativo en algún cierre. Es un efecto de las filas excluidas por cantidad vacía y habría que auditar esos movimientos.

## Cómo reproducirlo
```bash
python3 generar_datos.py   # opcional: regenera los CSV crudos
python3 run.py             # carga a SQLite, ejecuta los .sql y exporta output/*.csv
```
También puedes abrir `output/proyecto.db` con DB Browser for SQLite y ejecutar los `.sql` uno por uno.

## Power BI
Importa de `output/`: `kpi_sku.csv`, `kpi_mensual.csv`, `kpi_categoria.csv`, `stock_mensual.csv`.

```dax
Costo Salidas = SUM ( kpi_sku[cogs] )
Inventario Promedio = SUM ( kpi_sku[inv_prom_valor] )
Rotación = DIVIDE ( [Costo Salidas], [Inventario Promedio] )
Días de Inventario = DIVIDE ( 365, [Rotación] )
SKUs Alto o Exceso = CALCULATE ( COUNTROWS ( kpi_sku ), kpi_sku[dias_inventario] > 90 )
```
Visuales sugeridos: 4 tarjetas (los KPIs), líneas con `kpi_mensual` (inventario al cierre y costo de salidas), barras de días de inventario por categoría, columnas por clase ABC y una tabla de SKUs filtrada por estado. Segmentadores: categoría y clase ABC.

## Limitaciones
- El inventario inicial simulado contiene exceso que se consume durante el año, por eso el valor al cierre baja en los primeros meses.
- La rotación usa salidas valorizadas a costo; con ventas reales se complementaría con margen y nivel de servicio.
""")

# ---------------- P2 ----------------
p = "p2_otif"; g = rd(p, "kpi_global").iloc[0]; m = rd(p, "kpi_mensual"); t = rd(p, "kpi_transportista"); z = rd(p, "kpi_zona"); mo = rd(p, "kpi_motivo")
open(f"{R}/{p}/README.md", "w", encoding="utf-8").write(f"""# Proyecto 2 · Nivel de servicio OTIF

> Datos **simulados** (no provienen de ninguna empresa). Se generaron con errores de calidad a propósito.

## Pregunta de negocio
¿Qué porcentaje de pedidos llega a tiempo y completo, y dónde y por qué se pierde el servicio?

## Datos
| Archivo | Contenido |
|---|---|
| `data/despachos.csv` | Pedidos con fecha de pedido, compromiso y entrega, cantidades, transportista y motivo de falla (oct 2025 – sep 2026) |
| `data/clientes.csv` | 40 clientes con canal y zona |

## Limpieza (`sql/00_diagnostico.sql` y `sql/01_limpieza.sql`)
{calidad(p)}

## Métricas (`sql/02_kpis.sql`)
- **A tiempo** = fecha de entrega ≤ fecha compromiso. **Completo** = cantidad entregada ≥ pedida. **OTIF** = ambas a la vez, por pedido.
- **Fill rate** = suma de min(entregado, pedido) ÷ suma de pedido (unidades).
- El mes se asigna por fecha compromiso y solo se evalúan compromisos dentro del periodo.
- **Pareto de causas** con porcentaje acumulado calculado con funciones de ventana.

## Resultados
- OTIF global **{g.pct_otif:.1f}%** (a tiempo {g.pct_a_tiempo:.1f}%, completo {g.pct_completo:.1f}%, fill rate {g.fill_rate:.1f}%) sobre {int(g.pedidos_evaluados):,} pedidos.
- Tendencia: de **{m.pct_otif.iloc[0]:.1f}%** en {m.mes.iloc[0]} a **{m.pct_otif.iloc[-1]:.1f}%** en {m.mes.iloc[-1]}.
- Transportistas: {t.iloc[0].transportista} {t.iloc[0].pct_otif:.1f}% frente a {t.iloc[-1].transportista} {t.iloc[-1].pct_otif:.1f}%. La brecha viene de la puntualidad.
- Zona más débil: **{z.iloc[-1].zona}** con {z.iloc[-1].pct_otif:.1f}% de OTIF.
- Las dos primeras causas ({mo.iloc[0].motivo} y {mo.iloc[1].motivo}) explican el {mo.iloc[1].pct_acumulado:.0f}% de los pedidos fallidos.

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
""")

# ---------------- P3 ----------------
p = "p3_productividad"; g = rd(p, "kpi_global").iloc[0]; per = rd(p, "kpi_periodo"); tu = rd(p, "kpi_turno"); op = rd(p, "kpi_operador"); an = rd(p, "kpi_antiguedad")
open(f"{R}/{p}/README.md", "w", encoding="utf-8").write(f"""# Proyecto 3 · Productividad de picking

> Datos **simulados** (no provienen de ninguna empresa). Se generaron con errores de calidad a propósito.

## Pregunta de negocio
¿Cuántas líneas por hora pickea el equipo frente a la meta de cada zona, y qué turnos, zonas y operadores explican la brecha?

## Datos
| Archivo | Contenido |
|---|---|
| `data/picking.csv` | Registro por operador y día: zona, líneas, unidades, horas y errores (abr – sep 2026) |
| `data/operadores.csv` | 14 operadores con turno, antigüedad y zona principal |
| `data/metas.csv` | Meta de líneas por hora por zona |

## Limpieza (`sql/00_diagnostico.sql` y `sql/01_limpieza.sql`)
{calidad(p)}

Detalle técnico: `UPPER` y `LOWER` de SQLite no convierten la Ñ, por eso el turno se normaliza por su primera letra.

## Métricas (`sql/02_kpis.sql`)
- **Líneas por hora** = suma de líneas ÷ suma de horas. Es un promedio ponderado: promediar los ratios diarios daría el mismo peso a un día de 3 horas que a uno de 8.
- **Cumplimiento de meta** = suma de líneas ÷ suma de (horas × meta de la zona).
- **Error de picking** = errores ÷ líneas.
- Cortes por mes, semana, turno, zona, día de la semana, antigüedad y operador (ranking con `RANK()`).

## Resultados
- **{g.lph:.1f} líneas por hora**, cumplimiento de meta **{g.cumplimiento_meta_pct:.1f}%** y error de **{g.error_pct:.2f}%**.
- Antes de julio {per.cumplimiento_meta_pct.iloc[0]:.1f}%; desde julio {per.cumplimiento_meta_pct.iloc[1]:.1f}%. La comparación no prueba causalidad porque también cambia la madurez del equipo.
- Turno noche: {tu[tu.turno=='Noche'].cumplimiento_meta_pct.iloc[0]:.1f}% frente a {tu[tu.turno=='Mañana'].cumplimiento_meta_pct.iloc[0]:.1f}% del turno mañana.
- {int((op.cumplimiento_meta_pct < 100).sum())} de {len(op)} operadores quedan bajo la meta. Con menos de 6 meses de antigüedad el cumplimiento es {an.cumplimiento_meta_pct.iloc[0]:.1f}%.

## Cómo reproducirlo
```bash
python3 generar_datos.py
python3 run.py
```

## Power BI
Importa de `output/`: `picking_valido.csv` (hechos), `kpi_operador.csv` y `metas.csv`.

```dax
Líneas = SUM ( picking_valido[lineas] )
Horas = SUM ( picking_valido[horas] )
Líneas por Hora = DIVIDE ( [Líneas], [Horas] )
Líneas Esperadas = SUM ( picking_valido[lineas_esperadas] )
Cumplimiento Meta = DIVIDE ( [Líneas], [Líneas Esperadas] )
Error % = DIVIDE ( SUM ( picking_valido[errores] ), [Líneas] )
```
Cuida que `Líneas por Hora` sea una medida y no el promedio de la columna `lph`; así queda ponderada por horas. Visuales sugeridos: tarjetas, línea semanal de cumplimiento con constante de 100%, barras por turno, zona y operador, y matriz turno × día.

## Limitaciones
- Las metas por zona son supuestos del ejercicio.
- No hay datos de volumen de pedidos ni de tipo de SKU, que también explican la productividad.
""")

# ---------------- README general ----------------
open(f"{R}/README.md", "w", encoding="utf-8").write("""# Portafolio de analítica logística

Tres proyectos con SQL (SQLite) sobre operaciones de almacén y distribución, con datos **simulados** que incluyen errores de calidad a propósito.

| Proyecto | Pregunta | Carpeta |
|---|---|---|
| 1. Rotación de inventario | ¿Cuántas veces rota y qué SKUs inmovilizan capital? | `p1_rotacion_inventario/` |
| 2. Nivel de servicio OTIF | ¿Cuánto llega a tiempo y completo, y por qué falla? | `p2_otif/` |
| 3. Productividad de picking | ¿Cómo rinde el equipo frente a la meta? | `p3_productividad/` |

Cada carpeta tiene `data/` (CSV crudos), `sql/` (diagnóstico, limpieza y KPIs), `output/` (tablas listas para Power BI), `run.py`, `generar_datos.py` y un `README.md` con definiciones, resultados y medidas DAX.

## Flujo de trabajo de cada proyecto
1. Diagnosticar la calidad de los datos con consultas de conteo.
2. Limpiar con reglas explícitas y documentadas.
3. Calcular KPIs con SQL (CTE, funciones de ventana, agregaciones ponderadas).
4. Exportar a CSV para el modelo de Power BI.
5. Verificar con un recálculo independiente (`verificar_pandas.py`).

## Archivos de la raíz
- `dashboard.html`: tablero con los tres proyectos (ábrelo en el navegador).
- `verificar_pandas.py`: recalcula los KPIs globales con pandas desde los CSV crudos y los compara con SQL.
- `build_dashboard.py`: regenera el tablero desde `output/`.

## Cómo presentarlo
- Declara siempre que los datos son simulados. Un reclutador lo valora más que un dato inventado presentado como real.
- No lo muestres como experiencia laboral. Ponlo en una sección **Proyectos** del CV y en LinkedIn, con el problema de negocio, la herramienta y un resultado concreto.
- Ejemplo de línea para el CV: *Proyecto: análisis de rotación de inventario con SQL y Power BI (datos simulados); limpieza de 5 tipos de error, clasificación ABC y detección de 10 SKUs con más de 90 días de cobertura.*
- Para que cuente como Power BI, falta construir el informe `.pbix` con estos CSV. Las medidas DAX ya están en cada README.
""")
print("ok")
