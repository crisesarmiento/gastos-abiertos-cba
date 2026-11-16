"""Ingesta de ZIPs oficiales -> DuckDB + Parquet + CSV, con validación de totales."""
import csv, hashlib, json, re, zipfile
from decimal import Decimal
from pathlib import Path
import duckdb
from .parse import read_gastos, read_recursos

SCHEMA = Path(__file__).resolve().parents[2] / "docs" / "schema.sql"
TOL = Decimal("1")

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def safe_extract(zpath, dest):
    """Extrae XLSX a un directorio propio, rechazando rutas fuera de dest."""
    dest.mkdir(parents=True, exist_ok=True)
    out = []
    with zipfile.ZipFile(zpath) as z:
        for info in z.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".xlsx"):
                continue
            target = (dest / Path(info.filename).name).resolve()
            if dest.resolve() not in target.parents:
                continue
            target.write_bytes(z.read(info))
            out.append(target)
    return out

def classify(name):
    n = name.lower()
    kind = "gastos" if n.startswith("gastos") else "recursos" if n.startswith("recursos") else None
    tipo = "EMAEE" if "emaee" in n else "AC"
    return kind, tipo

def ingest(raw_dir, out_dir):
    raw_dir, out_dir = Path(raw_dir), Path(out_dir)
    ext_root = raw_dir / "extracted"
    out_dir.mkdir(parents=True, exist_ok=True)
    gastos, recursos, metas, checks = [], [], [], []
    for z in sorted((raw_dir / "zips").glob("*.zip")):
        files = safe_extract(z, ext_root / z.stem)
        for f in files:
            kind, tipo = classify(f.name)
            if not kind:
                continue
            cid = f"{z.stem}::{f.name}"
            if kind == "gastos":
                rows, _ = read_gastos(f, tipo)
                for r in rows:
                    r["corrida_id"] = cid
                gastos += rows
                for col in ("presupuesto_vigente", "compromiso", "devengado", "pagado"):
                    src = sum((r["_raw"][col.upper().replace("_", " ")] or 0) for r in rows)
                    got = sum((r[col] or 0) for r in rows)
                    checks.append(dict(corrida=cid, columna=col, fuente=str(src), base=str(got), ok=abs(Decimal(src) - got) <= TOL))
            else:
                rows = read_recursos(f, tipo)
                for r in rows:
                    r["corrida_id"] = cid
                recursos += rows
            metas.append((cid, f"zip:{kind}", str(z.name), None, len(rows), sha256(f), None))
    return gastos, recursos, metas, checks

def write_db(gastos, recursos, metas, out_dir):
    out_dir = Path(out_dir)
    db = out_dir / "gastos.duckdb"
    if db.exists():
        db.unlink()
    con = duckdb.connect(str(db))
    # esquema base de docs/schema.sql (idempotente: se recrea todo)
    con.execute(SCHEMA.read_text())
    # dimensiones desde el corte más reciente de cada ejercicio
    latest = {}
    for r in gastos:
        k = (r["tipo"], r["ejercicio"])
        latest[k] = max(latest.get(k, r["fecha_corte"]), r["fecha_corte"])
    cur = [r for r in gastos if r["fecha_corte"] == latest[(r["tipo"], r["ejercicio"])]]
    con.executemany("INSERT INTO dim_ejercicio VALUES (?, NULL) ON CONFLICT DO NOTHING", [(e,) for e in sorted({r["ejercicio"] for r in gastos})])
    seen = {}
    for r in cur:
        seen[("j", r["ejercicio"], r["jurisdiccion_codigo"], r["tipo"])] = r["jurisdiccion_nombre"]
    con.executemany("INSERT INTO dim_jurisdiccion VALUES (?,?,?,?,NULL)", [(k[1], k[2], v, k[3]) for k, v in seen.items()])
    uni = {(r["ejercicio"], r["jurisdiccion_codigo"], r["unidad_codigo"]): r["unidad_nombre"] for r in cur}
    con.executemany("INSERT INTO dim_unidad VALUES (?,?,?,?,NULL)", [(*k, v) for k, v in uni.items()])
    pro = {(r["ejercicio"], r["jurisdiccion_codigo"], r["unidad_codigo"], r["programa_codigo"]): r["programa_nombre"] for r in cur}
    con.executemany("INSERT INTO dim_programa VALUES (?,?,?,?,?,NULL)", [(*k, v) for k, v in pro.items()])
    par = {(r["ejercicio"], r["partida_principal"]): r["partida_nombre"] for r in cur}
    con.executemany("INSERT INTO dim_partida VALUES (?,?,?,'principal',NULL)", [(*k, v) for k, v in par.items()])
    con.executemany(
        "INSERT INTO hecho_agregado VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [(r["tipo"], r["ejercicio"], r["mes"], r["fecha_corte"], r["jurisdiccion_codigo"],
          f'{r["unidad_codigo"]} - {r["unidad_nombre"]}', f'{r["programa_codigo"]} - {r["programa_nombre"]}',
          r["partida_principal"], f'{r["finalidad"]} - {r["finalidad_nombre"]}', f'{r["funcion"]} - {r["funcion_nombre"]}',
          r["presupuesto_vigente"], r["compromiso"], r["devengado"], r["pagado"], r["corrida_id"]) for r in gastos])
    con.execute("""CREATE TABLE hecho_recurso (tipo VARCHAR, ejercicio INTEGER, mes INTEGER, fecha_corte DATE,
        jurisdiccion VARCHAR, principal VARCHAR, parcial VARCHAR, sub_parcial VARCHAR,
        presupuesto_vigente DECIMAL(18,2), recaudacion DECIMAL(18,2), corrida_id VARCHAR)""")
    con.executemany("INSERT INTO hecho_recurso VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [(r["tipo"], r["AÑO"], r["MES"], r["fecha_corte"], r.get("JURISDICCION"), r["PRINCIPAL"], r.get("PARCIAL"),
          r.get("SUB PARCIAL"), r["PRESUPUESTO VIGENTE"], r["RECAUDACION"], r["corrida_id"]) for r in recursos])
    con.executemany("INSERT INTO meta_corrida VALUES (?,?,?,CURRENT_TIMESTAMP AT TIME ZONE 'UTC',?,?,?)",
                    [(m[0], m[1], m[2], m[4], m[5], m[6]) for m in metas])
    # vista: solo el último corte por (tipo, ejercicio) -> evita sumar acumulados dos veces
    con.execute("""CREATE VIEW v_agregado_ultimo_corte AS SELECT * FROM hecho_agregado
        QUALIFY fecha_corte = MAX(fecha_corte) OVER (PARTITION BY tipo, ejercicio)""")
    for t in ("hecho_agregado", "hecho_recurso", "dim_jurisdiccion", "dim_unidad", "dim_programa", "dim_partida"):
        con.execute(f"COPY {t} TO '{out_dir}/{t}.parquet' (FORMAT PARQUET)")
        con.execute(f"COPY {t} TO '{out_dir}/{t}.csv' (HEADER, DELIMITER ',')")
    con.close()
    return db

def validate_db(db, checks):
    """Compara sumas leídas desde la base con las de las fuentes (por archivo)."""
    con = duckdb.connect(str(db), read_only=True)
    res = []
    for cid, col, src in [(c["corrida"], c["columna"], Decimal(c["fuente"])) for c in checks]:
        got = con.execute(f"SELECT COALESCE(SUM({col}),0) FROM hecho_agregado WHERE corrida_id=?", [cid]).fetchone()[0]
        res.append(dict(corrida=cid, columna=col, fuente=str(src), base=str(got), ok=abs(src - Decimal(got)) <= TOL))
    con.close()
    return res

def run(raw_dir="data/raw", out_dir="data/processed"):
    gastos, recursos, metas, _ = ingest(raw_dir, out_dir)
    checks = [c for c in _]
    db = write_db(gastos, recursos, metas, out_dir)
    res = validate_db(db, checks)
    Path(out_dir, "validacion.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    return db, res, len(gastos), len(recursos)
