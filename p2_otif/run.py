"""Carga los CSV crudos en SQLite, ejecuta los scripts SQL en orden y exporta los resultados."""
import csv, glob, os, sqlite3, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(AQUI, "output", "proyecto.db")
# Tablas que se exportan a output/*.csv (para Power BI)
EXPORTAR = ["calidad_datos", "despachos_limpio", "otif_pedidos", "clientes", "kpi_global", "kpi_mensual",
            "kpi_transportista", "kpi_canal", "kpi_zona", "kpi_cliente", "kpi_motivo"]


def cargar_csv(con, ruta, tabla):
    with open(ruta, newline="", encoding="utf-8") as f:
        filas = list(csv.reader(f))
    cols = filas[0]
    con.execute(f"DROP TABLE IF EXISTS {tabla}")
    con.execute(f"CREATE TABLE {tabla} ({', '.join(c + ' TEXT' for c in cols)})")
    con.executemany(f"INSERT INTO {tabla} VALUES ({','.join('?' * len(cols))})", filas[1:])


def exportar(con, tabla):
    cur = con.execute(f"SELECT * FROM {tabla}")
    with open(os.path.join(AQUI, "output", f"{tabla}.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([d[0] for d in cur.description])
        w.writerows(cur.fetchall())


if __name__ == "__main__":
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    for ruta in sorted(glob.glob(os.path.join(AQUI, "data", "*.csv"))):   # cada CSV -> tabla <nombre>_raw
        cargar_csv(con, ruta, os.path.splitext(os.path.basename(ruta))[0] + "_raw")
    for script in sorted(glob.glob(os.path.join(AQUI, "sql", "*.sql"))):
        con.executescript(open(script, encoding="utf-8").read())
    con.commit()
    for t in EXPORTAR:
        exportar(con, t)
    print("Calidad de datos:")
    for r in con.execute("SELECT * FROM calidad_datos"):
        print("  ", r)
    print("KPI global:", con.execute("SELECT * FROM kpi_global").fetchone())
    con.close()
