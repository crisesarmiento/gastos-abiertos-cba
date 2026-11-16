import io
import zipfile
from datetime import date
from decimal import Decimal

import openpyxl
import pytest

from gastos_abiertos.ingest import ingest, write_db, validate_db
from gastos_abiertos.parse import GASTO_COLS


def _ac_header():
    return GASTO_COLS[:]


def _emaee_header():
    return [c for c in GASTO_COLS if c != "COMPROMISO"]


def _ac_row(ejercicio, mes, jur, uni, prog, partida, finalidad, funcion,
            vigente, compromiso, devengado, pagado):
    return [ejercicio, mes, jur, uni, prog, partida, finalidad, funcion,
            vigente, compromiso, devengado, pagado]


def _emaee_row(ejercicio, mes, jur, uni, prog, partida, finalidad, funcion,
               vigente, devengado, pagado):
    return [ejercicio, mes, jur, uni, prog, partida, finalidad, funcion,
            vigente, devengado, pagado]


def _write_xlsx(path, header, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(header)
    for r in rows:
        ws.append(r)
    # filas vacías como en los XLSX reales
    ws.append([None] * len(header))
    ws.append([""] * len(header))
    wb.save(path)


def _make_zip(zips_dir, name):
    zpath = zips_dir / name
    zips_dir.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # AC marzo
        ac_mar = io.BytesIO()
        _write_xlsx(ac_mar, _ac_header(), [
            _ac_row(2025, 3, "101 - J1", "0101 - U1", "1 - P1", "1 - Partida",
                    "1 - F", "1 - Fn", 1000.1234, 800.0, 500.0, 250.0),
            _ac_row(2025, 3, "102 - J2", "0201 - U2", "2 - P2", "2 - Partida",
                    "2 - F", "2 - Fn", 2000.0, 1500.5, 1000.0, 500.0),
        ])
        zf.writestr("Gastos_AC_2025_03.xlsx", ac_mar.getvalue())

        # AC junio (mismo ejercicio, corte más reciente)
        ac_jun = io.BytesIO()
        _write_xlsx(ac_jun, _ac_header(), [
            _ac_row(2025, 6, "101 - J1", "0101 - U1", "1 - P1", "1 - Partida",
                    "1 - F", "1 - Fn", 3000.0, 2000.0, 1500.75, 750.0),
        ])
        zf.writestr("Gastos_AC_2025_06.xlsx", ac_jun.getvalue())

        # EMAEE marzo
        emaee_mar = io.BytesIO()
        _write_xlsx(emaee_mar, _emaee_header(), [
            _emaee_row(2025, 3, "200 - E1", "001 - UE1", "1 - PE1", "1 - Partida",
                       "1 - F", "1 - Fn", 5000.0, 2500.0, 1000.0),
        ])
        zf.writestr("Gastos_EMAEE_2025_03.xlsx", emaee_mar.getvalue())

        # intento de zip-slip: debe ignorarse
        zf.writestr("../evil.xlsx", b"malicious")

    zpath.write_bytes(buf.getvalue())
    return zpath


def test_ingest_zip_fixture(tmp_path):
    zips_dir = tmp_path / "zips"
    _make_zip(zips_dir, "test_2025.zip")

    gastos, recursos, metas, checks = ingest(tmp_path, tmp_path / "processed")

    # 2 AC mar + 1 AC jun + 1 EMAEE mar = 4
    assert len(gastos) == 4
    assert len(recursos) == 0
    assert len(metas) == 3  # una por XLSX extraído

    db = write_db(gastos, recursos, metas, tmp_path / "processed")
    validation = validate_db(db, checks)

    failed = [v for v in validation if not v["ok"]]
    assert failed == []

    import duckdb
    con = duckdb.connect(str(db), read_only=True)

    # total devengado AC debe ser la suma de los tres registros AC
    total_ac = con.execute(
        "SELECT COALESCE(SUM(devengado),0) FROM hecho_agregado WHERE tipo='AC'"
    ).fetchone()[0]
    assert Decimal(total_ac) == Decimal("500.00") + Decimal("1000.00") + Decimal("1500.75")

    # v_agregado_ultimo_corte no debe sumar marzo y junio del mismo ejercicio
    ultimo_ac = con.execute(
        "SELECT COALESCE(SUM(devengado),0) FROM v_agregado_ultimo_corte "
        "WHERE tipo='AC' AND ejercicio=2025"
    ).fetchone()[0]
    assert Decimal(ultimo_ac) == Decimal("1500.75")

    # EMAEE: compromiso NULL y solo corte marzo
    emaee = con.execute(
        "SELECT presupuesto_vigente, compromiso, devengado FROM hecho_agregado WHERE tipo='EMAEE'"
    ).fetchall()
    assert len(emaee) == 1
    assert emaee[0] == (Decimal("5000.00"), None, Decimal("2500.00"))

    con.close()


def test_safe_extract_ignores_zip_slip(tmp_path):
    zips_dir = tmp_path / "zips"
    _make_zip(zips_dir, "slip.zip")

    # ingest ya usa safe_extract; verificamos que no escribió fuera de extracted
    gastos, _, _, _ = ingest(tmp_path, tmp_path / "processed")
    # si evil.xlsx se hubiera extraído fuera, no afectaría el conteo de filas
    # porque no es un XLSX válido, pero validamos que no exista fuera
    assert not (tmp_path / "evil.xlsx").exists()
    assert len(gastos) == 4
