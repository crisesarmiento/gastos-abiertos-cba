"""Parseo de XLSX oficiales de ejecución presupuestaria (gastos y recursos)."""
import calendar, re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import openpyxl

CENT = Decimal("0.01")
GASTO_COLS = ["AÑO", "MES", "JURISDICCION", "UNIDAD ADMINISTRATIVA", "PROGRAMA", "PARTIDA PRINCIPAL",
              "FINALIDAD", "FUNCION", "PRESUPUESTO VIGENTE", "COMPROMISO", "DEVENGADO", "PAGADO"]
MONEY = ["PRESUPUESTO VIGENTE", "COMPROMISO", "DEVENGADO", "PAGADO"]

def money(x):
    """Decimal con centavos; vacío/None -> None."""
    if x is None or x == "":
        return None
    return Decimal(repr(x) if isinstance(x, float) else str(x)).quantize(CENT, ROUND_HALF_UP)

def money_raw(x):
    """Sin redondear (para validar totales contra la fuente)."""
    if x is None or x == "":
        return None
    return Decimal(repr(x) if isinstance(x, float) else str(x))

def split_code(s):
    """'101 - Nombre' | '01 . Personal' -> ('101', 'Nombre'). Código solo dígitos."""
    if s is None:
        return None, None
    m = re.match(r"^\s*(\d+)\s*[-.]\s*(.*?)\s*$", str(s))
    return (m.group(1), m.group(2)) if m else (None, str(s).strip())

def fecha_corte(anio, mes):
    return date(int(anio), int(mes), calendar.monthrange(int(anio), int(mes))[1])

def norm_cuit(s):
    d = re.sub(r"\D", "", str(s or ""))
    return d if len(d) == 11 else None

def read_gastos(path, tipo):
    """Devuelve (filas, notas). tipo AC|EMAEE. Salta filas vacías; valida cabecera."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    it = ws.iter_rows(values_only=True)
    header = [h for h in next(it) if h]
    expected = [c for c in GASTO_COLS if not (tipo == "EMAEE" and c == "COMPROMISO")]
    if header != expected:
        raise ValueError(f"{path}: cabecera inesperada {header}")
    out = []
    for r in it:
        if r[2] in (None, ""):
            continue
        d = dict(zip(header, r))
        jc, jn = split_code(d["JURISDICCION"]); uc, un = split_code(d["UNIDAD ADMINISTRATIVA"])
        pc, pn = split_code(d["PROGRAMA"]); ic, inn = split_code(d["PARTIDA PRINCIPAL"])
        fc, fn = split_code(d["FINALIDAD"]); fuc, fun = split_code(d["FUNCION"])
        out.append(dict(
            tipo=tipo, ejercicio=int(d["AÑO"]), mes=int(d["MES"]), fecha_corte=fecha_corte(d["AÑO"], d["MES"]),
            jurisdiccion_codigo=jc, jurisdiccion_nombre=jn, unidad_codigo=uc, unidad_nombre=un,
            programa_codigo=pc, programa_nombre=pn, partida_principal=ic, partida_nombre=inn,
            finalidad=fc, finalidad_nombre=fn, funcion=fuc, funcion_nombre=fun,
            **{k.lower().replace(" ", "_"): money(d.get(k)) for k in MONEY},
            _raw={k: money_raw(d.get(k)) for k in MONEY},
        ))
    notas = []
    if len(wb.worksheets) > 1:
        for r in wb.worksheets[1].iter_rows(values_only=True):
            notas += [str(x) for x in r if x]
    return out, notas

def read_recursos(path, tipo):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    it = wb.worksheets[0].iter_rows(values_only=True)
    header = [h for h in next(it) if h]
    out = []
    for r in it:
        d = dict(zip(header, r))
        if d.get("PRINCIPAL") in (None, ""):
            continue
        d["tipo"] = tipo
        d["fecha_corte"] = fecha_corte(d["AÑO"], d["MES"])
        d["PRESUPUESTO VIGENTE"] = money(d.get("PRESUPUESTO VIGENTE")); d["RECAUDACION"] = money(d.get("RECAUDACION"))
        out.append(d)
    return out
