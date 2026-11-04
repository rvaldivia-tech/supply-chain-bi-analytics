"""Genera datos SIMULADOS de un almacén de consumo masivo (Lima) con errores de calidad realistas.

Lógica:
- 60 SKUs con demanda tipo Pareto (pocos SKUs concentran la mayor parte de las salidas).
- Stock inicial = demanda esperada x días de cobertura (algunos SKUs con exceso, otros ajustados).
- Reposición por punto de pedido con lead time de 5 días.
- Después se ensucian los datos: nulos, negativos, fechas mixtas, SKUs con espacios y duplicados.
Datos ficticios; no provienen de ninguna empresa real.
"""
import csv, random, math, os
from datetime import date, timedelta

random.seed(7)
AQUI = os.path.dirname(os.path.abspath(__file__))
INICIO = date(2025, 10, 1)
DIAS = 365
LEAD = 5

CATS = {  # costo min, costo max, cantidad base por salida
    "Abarrotes": (2, 15, 24), "Bebidas": (1.5, 12, 36), "Limpieza": (3, 25, 12),
    "Cuidado Personal": (4, 40, 10), "Snacks": (1, 8, 30),
}

# ---------- maestro ----------
n = 60
pesos = [(i + 1) ** -0.95 for i in range(n)]
random.shuffle(pesos)
tot = sum(pesos)
SALIDAS_DIA = 17.0                       # salidas promedio por día hábil
dias_habiles = sum(1 for d in range(DIAS) if (INICIO + timedelta(d)).weekday() != 6)

prods = []
for i in range(n):
    cat = random.choice(list(CATS))
    lo, hi, qb = CATS[cat]
    w = pesos[i] / tot
    qty_medio = qb * random.uniform(0.6, 1.4)
    demanda_dia = SALIDAS_DIA * w * qty_medio * (dias_habiles / DIAS)   # unidades por día calendario
    r = random.random()
    if r < 0.10:   cobertura = random.uniform(10, 25)      # riesgo de quiebre
    elif r < 0.55: cobertura = random.uniform(35, 90)     # saludable
    elif r < 0.80: cobertura = random.uniform(100, 180)    # alto
    else:          cobertura = random.uniform(200, 400)   # exceso (suele ser baja rotación)
    prods.append(dict(sku=f"SKU{i+1:03d}", desc=f"Producto {i+1:03d}", cat=cat,
                      costo=round(random.uniform(lo, hi), 2), w=w, qty=qty_medio,
                      dem=demanda_dia, stock=max(20, int(demanda_dia * cobertura)),
                      pend=None))
    prods[-1]["stock0"] = prods[-1]["stock"]

# ---------- simulación ----------
mov = []
mid = 1
for d in range(DIAS):
    dia = INICIO + timedelta(d)
    # llegadas pendientes
    for p in prods:
        if p["pend"] and p["pend"][0] <= dia:
            q = p["pend"][1]
            mov.append([mid, dia.isoformat(), p["sku"], "ENTRADA", q, random.choice(["ALM-LIMA", "ALM-CALLAO"])]); mid += 1
            p["stock"] += q
            p["pend"] = None
    if dia.weekday() == 6:
        continue
    for _ in range(max(1, int(random.gauss(SALIDAS_DIA, 3)))):
        p = random.choices(prods, weights=[x["w"] for x in prods])[0]
        q = max(1, int(random.lognormvariate(math.log(p["qty"]), 0.45)))
        q = min(q, p["stock"])               # no se despacha lo que no hay
        if q <= 0:
            continue
        p["stock"] -= q
        mov.append([mid, dia.isoformat(), p["sku"], "SALIDA", q, random.choice(["ALM-LIMA", "ALM-CALLAO"])]); mid += 1
    # revisión de punto de pedido
    for p in prods:
        rop = p["dem"] * (LEAD + 14)
        if p["stock"] <= rop and not p["pend"]:
            p["pend"] = (dia + timedelta(LEAD), int(p["dem"] * 60))      # pide ~60 días de demanda

# ---------- ensuciar ----------
filas = [list(r) for r in mov]
for r in random.sample(filas, 25): r[4] = ""
for r in random.sample(filas, 15):
    if r[4] != "": r[4] = -abs(int(r[4]))
for r in random.sample(filas, 120):
    y, m, dd = r[1].split("-"); r[1] = f"{dd}/{m}/{y}"
for r in random.sample(filas, 40): r[2] = " " + r[2].lower() + " "
filas += [list(r) for r in random.sample(filas, 35)]
random.shuffle(filas)

os.makedirs(os.path.join(AQUI, "data"), exist_ok=True)
with open(os.path.join(AQUI, "data", "productos.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["sku", "descripcion", "categoria", "costo_unitario", "stock_inicial"])
    w.writerows([[p["sku"], p["desc"], p["cat"], p["costo"], p["stock0"]] for p in prods])
with open(os.path.join(AQUI, "data", "movimientos.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["id_mov", "fecha", "sku", "tipo", "cantidad", "almacen"]); w.writerows(filas)
print("SKUs:", len(prods), "| movimientos (con suciedad):", len(filas),
      "| salidas:", sum(1 for r in mov if r[3] == "SALIDA"), "| entradas:", sum(1 for r in mov if r[3] == "ENTRADA"))
