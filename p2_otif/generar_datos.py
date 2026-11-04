"""Genera datos SIMULADOS de despachos a clientes (Lima y provincias) con errores de calidad realistas.

- 40 clientes en 4 canales y 5 zonas.
- ~19 pedidos por día hábil durante 12 meses (oct-2025 a sep-2026).
- La probabilidad de retraso depende del transportista y la zona; la de entrega incompleta, del mes.
- El servicio mejora levemente durante el año.
Datos ficticios; no provienen de ninguna empresa real.
"""
import csv, os, random
from datetime import date, timedelta

random.seed(11)
AQUI = os.path.dirname(os.path.abspath(__file__))
INICIO, DIAS, CORTE = date(2025, 10, 1), 365, date(2026, 9, 30)

CANALES = {  # rango de unidades por pedido, peso en la cartera
    "Supermercado": ((300, 2000), 0.25),
    "Mayorista": ((200, 1200), 0.25),
    "Farmacia": ((50, 400), 0.25),
    "Tienda tradicional": ((20, 150), 0.25),
}
ZONAS = ["Lima Centro", "Lima Norte", "Lima Sur", "Callao", "Provincia"]
LEAD = {"Lima Centro": 2, "Lima Norte": 2, "Lima Sur": 2, "Callao": 2, "Provincia": 4}
TRANSP_POR_ZONA = {
    "Provincia": (["TransAndes", "LogiSur"], [0.55, 0.45]),
    "default": (["Flota propia", "RapidoLima", "TransAndes"], [0.45, 0.35, 0.20]),
}
P_TARDE = {"Flota propia": 0.05, "RapidoLima": 0.08, "LogiSur": 0.13, "TransAndes": 0.19}
MOT_TARDE = (["Retraso de transporte", "Tráfico o clima", "Documentación incompleta", "Cliente no disponible"], [45, 20, 15, 20])
MOT_CORTO = (["Quiebre de stock", "Error de picking", "Producto dañado"], [55, 25, 20])

clientes = []
for i in range(1, 41):
    canal = random.choices(list(CANALES), [v[1] for v in CANALES.values()])[0]
    clientes.append(dict(id=f"C{i:03d}", nombre=f"Cliente {i:03d}", canal=canal,
                         zona=random.choices(ZONAS, [0.22, 0.2, 0.18, 0.12, 0.28])[0]))

filas, pid = [], 1
for d in range(DIAS):
    dia = INICIO + timedelta(d)
    if dia.weekday() == 6:
        continue
    t = d / (DIAS - 1)                      # 0 -> 1 a lo largo del año
    for _ in range(max(5, int(random.gauss(19, 4)))):
        c = random.choice(clientes)
        transp = random.choices(*(TRANSP_POR_ZONA["Provincia"] if c["zona"] == "Provincia" else TRANSP_POR_ZONA["default"]))[0]
        lo, hi = CANALES[c["canal"]][0]
        pedida = random.randint(lo, hi)
        comp = dia + timedelta(LEAD[c["zona"]])
        p_tarde = P_TARDE[transp] * (1.30 - 0.55 * t) * (1.8 if c["zona"] == "Provincia" else 1.0)
        p_corto = 0.11 * (1.30 - 0.55 * t)
        tarde = random.random() < p_tarde
        corto = random.random() < p_corto
        if tarde:
            retraso = random.choices([1, 2, 3, 4, 5], [58, 24, 9, 6, 3])[0]
        else:
            retraso = random.choices([0, -1], [88, 12])[0]
        entrega = comp + timedelta(retraso)
        entregada = int(pedida * random.uniform(0.5, 0.95)) if corto else pedida
        motivo = ""
        if corto:
            motivo = random.choices(*MOT_CORTO)[0]
        elif tarde:
            motivo = random.choices(*MOT_TARDE)[0]
        filas.append([f"P{pid:06d}", dia.isoformat(), comp.isoformat(),
                      entrega.isoformat() if entrega <= CORTE else "",
                      c["id"], transp, pedida, entregada if entrega <= CORTE else "", motivo])
        pid += 1

# ---------- ensuciar ----------
for r in random.sample(filas, 150):
    for k in (1, 2, 3):
        if r[k]:
            y, m, dd = r[k].split("-"); r[k] = f"{dd}/{m}/{y}"
for r in random.sample(filas, 90):
    r[5] = random.choice([r[5].upper(), " " + r[5] + " ", r[5].replace(" ", "").lower()])
completos = [r for r in filas if r[3]]
for r in random.sample(completos, 20): r[7] = ""                       # cantidad entregada vacía
for r in random.sample(completos, 12): r[3], r[1] = r[1], r[3]          # fechas invertidas (entrega antes de pedido)
for r in random.sample([x for x in completos if x[7] != ""], 25):       # sobreentrega
    r[7] = int(r[6]) + random.randint(1, 20)
filas += [list(r) for r in random.sample(filas, 30)]                    # duplicados
random.shuffle(filas)

os.makedirs(os.path.join(AQUI, "data"), exist_ok=True)
with open(os.path.join(AQUI, "data", "despachos.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["id_pedido", "fecha_pedido", "fecha_compromiso", "fecha_entrega", "id_cliente",
                "transportista", "cant_pedida", "cant_entregada", "motivo_falla"])
    w.writerows(filas)
with open(os.path.join(AQUI, "data", "clientes.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["id_cliente", "cliente", "canal", "zona"])
    w.writerows([[c["id"], c["nombre"], c["canal"], c["zona"]] for c in clientes])
print("pedidos (con suciedad):", len(filas))
