"""Exporta JSON compacto para la web estática desde DuckDB (último corte por tipo y ejercicio)."""
import json
from pathlib import Path
import duckdb

def export(db="data/processed/gastos.duckdb", out="web/data"):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    c = duckdb.connect(db, read_only=True)
    rows = c.execute("""
      SELECT a.tipo, a.ejercicio, a.fecha_corte, a.jurisdiccion_codigo, j.nombre, a.unidad, a.programa, a.partida_principal,
             p.nombre, a.presupuesto_vigente, a.compromiso, a.devengado, a.pagado
      FROM v_agregado_ultimo_corte a
      LEFT JOIN dim_jurisdiccion j ON j.ejercicio=a.ejercicio AND j.codigo=a.jurisdiccion_codigo AND j.tipo=a.tipo
      LEFT JOIN dim_partida p ON p.ejercicio=a.ejercicio AND p.codigo=a.partida_principal
      ORDER BY 1,2,4,6,7,8""").fetchall()
    cols = ["tipo", "ejercicio", "fecha_corte", "jur_codigo", "jur_nombre", "unidad", "programa", "partida_codigo",
            "partida_nombre", "presupuesto_vigente", "compromiso", "devengado", "pagado"]
    def cell(v):
        # Decimal -> centavos enteros (sin floats); fechas ISO
        if hasattr(v, "as_tuple"):
            return int(v.scaleb(2).to_integral_value())
        return v.isoformat() if hasattr(v, "isoformat") else v
    data = {"unidad_monto": "centavos", "columnas": cols, "filas": [[cell(v) for v in r] for r in rows]}
    cortes = {f"{r[0]}-{r[1]}": r[2].isoformat() for r in rows}
    meta = {
        "cortes": cortes,
        "fuente": "https://transparencia.cba.gov.ar/ejecuciones-presupuestarias/",
        "atribucion": "Portal de Transparencia de la Provincia de Córdoba",
        "notas": [
            "Datos agregados de ejecución presupuestaria (ZIP oficiales). No incluyen CUIT, comprobante ni proveedor.",
            "Cada ejercicio muestra su último corte acumulado; 2026 es parcial.",
            "Excluye partidas 20 (erogaciones figurativas) y, en Administración Central, 21 (fondos de terceros).",
            "Montos en pesos corrientes nominales, sin ajuste por inflación. En gastos.json los montos son centavos enteros.",
            "La Administración Central (AC) y los entes descentralizados (EMAEE) se muestran por separado."],
    }
    (out / "gastos.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    return len(rows)

if __name__ == "__main__":
    print(export())
