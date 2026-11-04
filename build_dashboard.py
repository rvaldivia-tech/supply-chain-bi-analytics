"""Lee los CSV de output/ de cada proyecto y genera el dashboard HTML autocontenido."""
import json, os
import pandas as pd

R = os.path.dirname(os.path.abspath(__file__))
def rd(p, t):
    df = pd.read_csv(f"{R}/{p}/output/{t}.csv")
    return df.astype(object).where(df.notna(), None).to_dict("records")

sku = rd("p1_rotacion_inventario", "kpi_sku")
tot = sum(r["cogs"] for r in sku)
abc = []
for c in "ABC":
    g = [r for r in sku if r["clase_abc"] == c]
    dias = sorted(r["dias_inventario"] for r in g if r["dias_inventario"] is not None)
    h = len(dias) // 2
    abc.append(dict(clase=c, skus=len(g), pct_cogs=round(100 * sum(r["cogs"] for r in g) / tot, 1),
                    dias_mediana=dias[h] if len(dias) % 2 else (dias[h - 1] + dias[h]) / 2))
data = {
 "p1": dict(global_=rd("p1_rotacion_inventario", "kpi_global")[0], mensual=rd("p1_rotacion_inventario", "kpi_mensual"),
            categoria=rd("p1_rotacion_inventario", "kpi_categoria"), sku=sku, abc=abc),
 "p2": dict(global_=rd("p2_otif", "kpi_global")[0], mensual=rd("p2_otif", "kpi_mensual"),
            transportista=rd("p2_otif", "kpi_transportista"), zona=rd("p2_otif", "kpi_zona"), motivo=rd("p2_otif", "kpi_motivo")),
 "p3": dict(global_=rd("p3_productividad", "kpi_global")[0], semanal=rd("p3_productividad", "kpi_semanal"),
            periodo=rd("p3_productividad", "kpi_periodo"), turno=rd("p3_productividad", "kpi_turno"),
            zona=rd("p3_productividad", "kpi_zona"), dia=rd("p3_productividad", "kpi_dia"),
            antiguedad=rd("p3_productividad", "kpi_antiguedad"), operador=rd("p3_productividad", "kpi_operador")),
}
js = json.dumps(data, ensure_ascii=False, allow_nan=False).replace("global_", "global")
src = open(f"{R}/dashboard_src.html", encoding="utf-8").read().replace("__DATA__", js)
open(f"{R}/dashboard_artifact.html", "w", encoding="utf-8").write(src)
standalone = ('<!doctype html><html lang="es"><head><meta charset="utf-8">'
              '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
              '<style>html{color-scheme:light}body{margin:0}</style></head><body>' + src + '</body></html>')
open(f"{R}/dashboard.html", "w", encoding="utf-8").write(standalone)
print("dashboard OK", len(src) // 1024, "KB")
