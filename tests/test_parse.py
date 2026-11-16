from datetime import date
from decimal import Decimal
from gastos_abiertos.parse import money, split_code, fecha_corte, norm_cuit

def test_money_centavos():
    assert money(1495579794.28) == Decimal("1495579794.28")
    assert money(1264764626.558386) == Decimal("1264764626.56")
    assert money("") is None and money(None) is None

def test_split_code():
    assert split_code("101 - Dependencia Inmediata") == ("101", "Dependencia Inmediata")
    assert split_code("01 . Personal") == ("01", "Personal")

def test_fecha_corte_y_cuit():
    assert fecha_corte(2026, 3) == date(2026, 3, 31)
    assert norm_cuit("30-12345678-9") == "30123456789" and norm_cuit("123") is None
