"""Verificación independiente: recalcula los KPIs globales con pandas desde los CSV crudos
y los compara con lo que produjo SQL."""
import os
import numpy as np
import pandas as pd

R = os.path.dirname(os.path.abspath(__file__))


def fecha(s):
    s = s.astype("string").str.strip()
    iso = pd.to_datetime(s.where(~s.str.contains("/", na=False)), format="%Y-%m-%d", errors="coerce")
    dmy = pd.to_datetime(s.where(s.str.contains("/", na=False)), format="%d/%m/%Y", errors="coerce")
    return iso.fillna(dmy)


def cmp(nombre, sql, pdv, tol=0.01):
    ok = abs(float(sql) - float(pdv)) <= tol
    print(f"  {'OK ' if ok else 'ERR'} {nombre}: SQL={sql}  pandas={round(float(pdv), 4)}")
    return ok


todo = []

# ---------- P1 ----------
print("P1 Rotación de inventario")
d = f"{R}/p1_rotacion_inventario"
m = pd.read_csv(f"{d}/data/movimientos.csv", dtype=str).drop_duplicates("id_mov")
p = pd.read_csv(f"{d}/data/productos.csv")
m["sku"] = m.sku.str.strip().str.upper()
m["tipo"] = m.tipo.str.strip().str.upper()
m["f"] = fecha(m.fecha)
m["q"] = pd.to_numeric(m.cantidad, errors="coerce").abs()
m = m.dropna(subset=["q"])
m["mes"] = m.f.dt.strftime("%Y-%m")
m["signed"] = np.where(m.tipo == "ENTRADA", m.q, -m.q)
meses = sorted(m.mes.unique())
neto = m.pivot_table(index="sku", columns="mes", values="signed", aggfunc="sum", fill_value=0).reindex(columns=meses, fill_value=0)
neto = neto.reindex(p.sku, fill_value=0)
cierre = neto.cumsum(axis=1).add(p.set_index("sku").stock_inicial, axis=0)
costo = p.set_index("sku").costo_unitario
inv_prom = (cierre.mean(axis=1) * costo).sum()
cogs = (m[m.tipo == "SALIDA"].groupby("sku").q.sum().reindex(p.sku, fill_value=0) * costo).sum()
k = pd.read_csv(f"{d}/output/kpi_global.csv").iloc[0]
todo += [cmp("COGS anual", k.cogs_anual, cogs, 1),
         cmp("Inventario promedio $", k.inv_prom_valor, inv_prom, 1),
         cmp("Rotación global", k.rotacion_global, cogs / inv_prom, 0.01),
         cmp("Días de inventario", k.dias_inventario_global, 365 * inv_prom / cogs, 1)]

# ---------- P2 ----------
print("P2 OTIF")
d = f"{R}/p2_otif"
x = pd.read_csv(f"{d}/data/despachos.csv", dtype=str).drop_duplicates("id_pedido")
for c in ["fecha_pedido", "fecha_compromiso", "fecha_entrega"]:
    x[c] = fecha(x[c])
x["ped"] = pd.to_numeric(x.cant_pedida)
x["ent"] = pd.to_numeric(x.cant_entregada, errors="coerce")
x = x[x.fecha_entrega.notna() & x.ent.notna() & (x.fecha_entrega >= x.fecha_pedido) & (x.fecha_compromiso <= "2026-09-30")]
x["ot"] = x.fecha_entrega <= x.fecha_compromiso
x["inf"] = x.ent >= x.ped
x["otif"] = x.ot & x.inf
fill = np.minimum(x.ent, x.ped).sum() / x.ped.sum() * 100
k = pd.read_csv(f"{d}/output/kpi_global.csv").iloc[0]
todo += [cmp("Pedidos evaluados", k.pedidos_evaluados, len(x), 0),
         cmp("% a tiempo", k.pct_a_tiempo, x.ot.mean() * 100, 0.06),
         cmp("% completo", k.pct_completo, x.inf.mean() * 100, 0.06),
         cmp("% OTIF", k.pct_otif, x.otif.mean() * 100, 0.06),
         cmp("Fill rate", k.fill_rate, fill, 0.06)]

# ---------- P3 ----------
print("P3 Productividad")
d = f"{R}/p3_productividad"
y = pd.read_csv(f"{d}/data/picking.csv", dtype=str).drop_duplicates("id_registro")
meta = pd.read_csv(f"{d}/data/metas.csv").set_index("zona").meta_lineas_hora
y["l"] = pd.to_numeric(y.lineas, errors="coerce")
y["h"] = pd.to_numeric(y.horas, errors="coerce")
y["e"] = pd.to_numeric(y.errores)
y["u"] = pd.to_numeric(y.unidades)
y = y[(y.h > 0) & (y.h <= 12) & (y.l >= 0) & y.l.notna()]
esperadas = (y.h * y.zona.map(meta)).sum()
k = pd.read_csv(f"{d}/output/kpi_global.csv").iloc[0]
todo += [cmp("Registros válidos", k.registros, len(y), 0),
         cmp("Líneas por hora", k.lph, y.l.sum() / y.h.sum(), 0.06),
         cmp("Unidades por hora", k.uph, y.u.sum() / y.h.sum(), 0.06),
         cmp("Error %", k.error_pct, y.e.sum() / y.l.sum() * 100, 0.006),
         cmp("Cumplimiento meta %", k.cumplimiento_meta_pct, y.l.sum() / esperadas * 100, 0.06)]
print("\nRESULTADO:", "TODO COINCIDE" if all(todo) else "HAY DIFERENCIAS")
