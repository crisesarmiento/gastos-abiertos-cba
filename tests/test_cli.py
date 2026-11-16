import responses

from gastos_abiertos.cli import main
from gastos_abiertos.download import DEFAULT_CATALOG_URL


@responses.activate
def test_cli_download_official_blocked_returns_3(tmp_path):
    responses.add(responses.GET, DEFAULT_CATALOG_URL, status=403)
    code = main(["download-official", "--dry-run"])
    assert code == 3
