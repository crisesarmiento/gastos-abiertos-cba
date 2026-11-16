from datetime import date
from decimal import Decimal
import openpyxl
import pytest

from gastos_abiertos.parse import money, split_code, fecha_corte, norm_cuit, read_gastos, GASTO_COLS


def test_money_centavos():
    assert money(1495579794.28) == Decimal("1495579794.28")
    assert money(1264764626.558386) == Decimal("1264764626.56")
    assert money("") is None and money(None) is None


def test_money_edge_cases():
    assert money(0) == Decimal("0.00")
    assert money(-100.5) == Decimal("-100.50")
    assert money("-0.004") == Decimal("-0.00")
    assert money("1234.567") == Decimal("1234.57")


def test_split_code():
    assert split_code("101 - Dependencia Inmediata") == ("101", "Dependencia Inmediata")
    assert split_code("01 . Personal") == ("01", "Personal")


def test_fecha_corte_y_cuit():
    assert fecha_corte(2026, 3) == date(2026, 3, 31)
    assert norm_cuit("30-12345678-9") == "30123456789" and norm_cuit("123") is None


def test_norm_cuit_edge_cases():
    assert norm_cuit("") is None
    assert norm_cuit(None) is None
    assert norm_cuit("12-3456789-0") is None  # 10 dígitos
    assert norm_cuit("30-12345678-9 extra") == "30123456789"


def _write_gasto_sheet(ws, header, rows):
    ws.append(header)
    for r in rows:
        ws.append(r)
    # filas vacías al final (como los XLSX reales)
    ws.append([None] * len(header))
    ws.append([""] * len(header))


def _make_ac_row(ejercicio=2025, mes=3, jur="101 - J", uni="0101 - U", prog="1 - P",
                 partida="1 - Partida", finalidad="1 - F", funcion="1 - Fn",
                 vigente=1000.1234, compromiso=800.0, devengado=500.0, pagado=250.0):
    return [ejercicio, mes, jur, uni, prog, partida, finalidad, funcion,
            vigente, compromiso, devengado, pagado]


def _make_emaee_row(**kw):
    # EMAEE no tiene COMPROMISO
    row = _make_ac_row(**kw)
    return row[:9] + row[10:]


def test_read_gastos_ac_normaliza(tmp_path):
    path = tmp_path / "gastos_ac.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    _write_gasto_sheet(ws, GASTO_COLS, [
        _make_ac_row(jur="101 - Ministerio", uni="0101 - Secr", prog="1 - Prog",
                     partida="1 - Servicios", finalidad="1 - Principal",
                     funcion="1 - Admin", vigente=1000.1234, compromiso=800.558,
                     devengado=500.0, pagado=250.0),
    ])
    wb.save(path)

    rows, notas = read_gastos(path, "AC")
    assert len(rows) == 1
    r = rows[0]
    assert r["tipo"] == "AC"
    assert r["ejercicio"] == 2025
    assert r["mes"] == 3
    assert r["fecha_corte"] == date(2025, 3, 31)
    assert r["jurisdiccion_codigo"] == "101"
    assert r["jurisdiccion_nombre"] == "Ministerio"
    assert r["presupuesto_vigente"] == Decimal("1000.12")
    assert r["compromiso"] == Decimal("800.56")
    assert r["devengado"] == Decimal("500.00")
    assert r["pagado"] == Decimal("250.00")


def test_read_gastos_emaee_sin_compromiso(tmp_path):
    path = tmp_path / "gastos_emaee.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    header = [c for c in GASTO_COLS if c != "COMPROMISO"]
    _write_gasto_sheet(ws, header, [
        _make_emaee_row(jur="200 - Ente", vigente=3000.0, devengado=1500.0, pagado=1000.0),
    ])
    wb.save(path)

    rows, _ = read_gastos(path, "EMAEE")
    assert len(rows) == 1
    r = rows[0]
    assert r["tipo"] == "EMAEE"
    assert r["compromiso"] is None
    assert r["presupuesto_vigente"] == Decimal("3000.00")


def test_read_gastos_skip_empty_rows(tmp_path):
    path = tmp_path / "gastos_ac.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    _write_gasto_sheet(ws, GASTO_COLS, [
        _make_ac_row(),
        [2025, 3, None, None, None, None, None, None, None, None, None, None],
        ["", "", "", "", "", "", "", "", "", "", "", ""],
    ])
    wb.save(path)

    rows, _ = read_gastos(path, "AC")
    assert len(rows) == 1


def test_read_gastos_bad_header_raises(tmp_path):
    path = tmp_path / "gastos_bad.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["AÑO", "MES", "OTRA"])
    ws.append([2025, 3, "x"])
    wb.save(path)

    with pytest.raises(ValueError):
        read_gastos(path, "AC")
