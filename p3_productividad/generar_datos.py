"""Genera datos SIMULADOS de picking de un almacén (abr-sep 2026) con errores de calidad realistas.

- 14 operadores en 3 turnos y 4 zonas de picking.
- Productividad por zona, curva de aprendizaje por antigüedad, efecto del turno y del día de la semana.
- Un programa de mejora (slotting + capacitación) sube la productividad desde julio.
- Los errores suben con la inexperiencia, el turno noche y el ritmo.
Datos ficticios; no provienen de ninguna empresa real.
"""
import csv, math, os, random
from datetime import date, timedelta

random.seed(21)
AQUI = os.path.dirname(os.path.abspath(__file__))
INICIO, FIN = date(2026, 4, 1), date(2026, 9, 30)

ZONAS = {  # líneas/hora base, unidades por línea, meta líneas/hora
    "Pallet":        dict(base=38, upl=18, meta=36),
    "Estantería":    dict(base=52, upl=9,  meta=50),
    "Flow rack":     dict(base=70, upl=4,  meta=65),
    "Refrigerado":   dict(base=34, upl=6,  meta=32),
}
TURNO_F = {"Mañana": 1.00, "Tarde": 0.95, "Noche": 0.88}
TURNO_ERR = {"Mañana": 1.0, "Tarde": 1.2, "Noche": 1.7}
DIA_F = {0: 0.93, 1: 1.0, 2: 1.02, 3: 1.01, 4: 0.97, 5: 0.95}   # lunes..sábado

turnos = ["Mañana"] * 6 + ["Tarde"] * 5 + ["Noche"] * 3
ops = []
for i, t in enumerate(turnos, 1):
    ant = random.choice([2, 3]) if i in (4, 11) else random.randint(7, 48)   # dos ingresos recientes
    ops.append(dict(id=f"OP{i:02d}", turno=t, ant=ant, zona=random.choice(list(ZONAS)),
                    hab=random.lognormvariate(0, 0.12)))

filas, rid = [], 1
d = INICIO
while d <= FIN:
    if d.weekday() != 6:
        mejora = 1.0 if d < date(2026, 7, 1) else 1.07
        meses_extra = (d.year - 2026) * 12 + d.month - 4
        for o in ops:
            if random.random() > 0.93:        # ausencia
                continue
            zona = o["zona"] if random.random() < 0.75 else random.choice(list(ZONAS))
            z = ZONAS[zona]
            ant = o["ant"] + meses_extra
            aprendizaje = 0.72 + 0.28 * (1 - math.exp(-ant / 6))
            horas = max(3.0, random.gauss(7.0 if d.weekday() != 5 else 5.0, 0.7))
            fatiga = 0.96 if horas > 8 else 1.0
            lph = z["base"] * o["hab"] * aprendizaje * TURNO_F[o["turno"]] * DIA_F[d.weekday()] * mejora * fatiga
            lineas = max(1, int(lph * horas * random.gauss(1, 0.06)))
            unidades = int(lineas * z["upl"] * random.gauss(1, 0.08))
            tasa_err = 0.006 * TURNO_ERR[o["turno"]] * (1.6 if ant < 6 else 1.0) * (lph / z["base"]) * (0.8 if mejora > 1 else 1.0)
            errores = sum(1 for _ in range(lineas) if random.random() < tasa_err)
            filas.append([f"R{rid:05d}", d.isoformat(), o["id"], o["turno"], zona, lineas, unidades, round(horas, 2), errores])
            rid += 1
    d += timedelta(1)

# ---------- ensuciar ----------
for r in random.sample(filas, 80):
    y, m, dd = r[1].split("-"); r[1] = f"{dd}/{m}/{y}"
for r in random.sample(filas, 70):
    r[3] = random.choice([r[3].lower(), r[3].upper() + " ", "Manana" if r[3] == "Mañana" else r[3]])
for r in random.sample(filas, 15): r[7] = ""
for r in random.sample(filas, 10): r[7] = 0
for r in random.sample(filas, 8):  r[7] = round(float(r[7] or 7) * 10, 1)      # error de digitación: 72 en lugar de 7.2
for r in random.sample(filas, 12): r[5] = ""
for r in random.sample(filas, 6):  r[5] = -abs(int(r[5] or 100))
filas += [list(r) for r in random.sample(filas, 25)]
random.shuffle(filas)

os.makedirs(os.path.join(AQUI, "data"), exist_ok=True)
with open(os.path.join(AQUI, "data", "picking.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["id_registro", "fecha", "id_operador", "turno", "zona", "lineas", "unidades", "horas", "errores"])
    w.writerows(filas)
with open(os.path.join(AQUI, "data", "operadores.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["id_operador", "turno_asignado", "antiguedad_meses_inicio", "zona_principal"])
    w.writerows([[o["id"], o["turno"], o["ant"], o["zona"]] for o in ops])
with open(os.path.join(AQUI, "data", "metas.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["zona", "meta_lineas_hora"])
    w.writerows([[k, v["meta"]] for k, v in ZONAS.items()])
print("registros (con suciedad):", len(filas))
