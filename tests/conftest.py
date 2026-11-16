import pytest

@pytest.fixture(autouse=True)
def _aislar_cwd(tmp_path, monkeypatch):
    """Los tests no deben escribir logs/cache en el repo real (ni parecer requests reales)."""
    monkeypatch.chdir(tmp_path)
