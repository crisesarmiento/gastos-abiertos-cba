import io
import zipfile

import pytest
import responses

from gastos_abiertos.download import DEFAULT_CATALOG_URL, download_official
from gastos_abiertos.http import BlockedError, HttpClient


class FakeClock:
    def __init__(self):
        self.t = 0.0
        self.sleeps = []

    def sleep(self, s):
        self.sleeps.append(s)
        self.t += s

    def now(self):
        return self.t


@pytest.fixture
def tmp_client(tmp_path):
    clock = FakeClock()
    client = HttpClient(
        cache_dir=tmp_path / "cache",
        delay=10.0,
        log_path=tmp_path / "http.log",
        sleep=clock.sleep,
        now=clock.now,
    )
    return client, clock


def _catalog(urls):
    links = "\n".join(f'<a href="{u}">{u.rsplit("/", 1)[-1]}</a>' for u in urls)
    return f"<html><body>{links}</body></html>".encode("utf-8")


@responses.activate
def test_resume_skips_existing_file(tmp_path, tmp_client):
    client, _ = tmp_client
    urls = ["https://example.com/zips/gastos_2025_03.zip"]
    existing = tmp_path / "zips" / "gastos_2025_03.zip"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"already here")

    responses.add(responses.GET, DEFAULT_CATALOG_URL, body=_catalog(urls), status=200)

    result = download_official(DEFAULT_CATALOG_URL, raw_dir=tmp_path, client=client)
    assert result == []
    assert len(responses.calls) == 1  # solo catálogo


@responses.activate
def test_part_overwritten_and_renamed(tmp_path, tmp_client):
    client, _ = tmp_client
    urls = ["https://example.com/zips/gastos_2025_03.zip"]
    responses.add(responses.GET, DEFAULT_CATALOG_URL, body=_catalog(urls), status=200)
    responses.add(responses.GET, urls[0], body=b"new content", status=200)

    dest = tmp_path / "zips" / "gastos_2025_03.zip"
    part = dest.with_suffix(dest.suffix + ".part")
    dest.parent.mkdir(parents=True)
    part.write_bytes(b"stale part")

    result = download_official(DEFAULT_CATALOG_URL, raw_dir=tmp_path, client=client)

    assert result == [dest]
    assert dest.read_bytes() == b"new content"
    assert not part.exists()


@responses.activate
def test_dry_run_no_zip_downloads(tmp_path, tmp_client):
    client, _ = tmp_client
    urls = [
        "https://example.com/zips/gastos_2025_03.zip",
        "https://example.com/zips/gastos_2025_06.zip",
    ]
    responses.add(responses.GET, DEFAULT_CATALOG_URL, body=_catalog(urls), status=200)

    result = download_official(DEFAULT_CATALOG_URL, raw_dir=tmp_path, client=client, dry_run=True)

    assert len(result) == 2
    assert len(responses.calls) == 1  # solo catálogo, no requests de ZIPs


@responses.activate
def test_limit_caps_downloads(tmp_path, tmp_client):
    client, _ = tmp_client
    urls = [
        "https://example.com/zips/gastos_2025_03.zip",
        "https://example.com/zips/gastos_2025_06.zip",
    ]
    responses.add(responses.GET, DEFAULT_CATALOG_URL, body=_catalog(urls), status=200)
    responses.add(responses.GET, urls[0], body=b"zip1", status=200)

    result = download_official(DEFAULT_CATALOG_URL, raw_dir=tmp_path, client=client, limit=1)

    assert len(result) == 1
    assert result[0].name == "gastos_2025_03.zip"
    assert len(responses.calls) == 2


@responses.activate
def test_blocked_on_catalog_stops_with_exit(tmp_path, tmp_client):
    client, _ = tmp_client
    responses.add(responses.GET, DEFAULT_CATALOG_URL, status=403)

    with pytest.raises(BlockedError):
        download_official(DEFAULT_CATALOG_URL, raw_dir=tmp_path, client=client)

    assert len(responses.calls) == 1


@responses.activate
def test_blocked_on_zip_stops_no_more_requests(tmp_path, tmp_client):
    client, _ = tmp_client
    urls = [
        "https://example.com/zips/gastos_2025_03.zip",
        "https://example.com/zips/gastos_2025_06.zip",
    ]
    responses.add(responses.GET, DEFAULT_CATALOG_URL, body=_catalog(urls), status=200)
    responses.add(responses.GET, urls[0], status=403)

    with pytest.raises(BlockedError):
        download_official(DEFAULT_CATALOG_URL, raw_dir=tmp_path, client=client)

    assert len(responses.calls) == 2


def test_main_blocked_returns_3(tmp_path):
    from gastos_abiertos.download import main
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, DEFAULT_CATALOG_URL, status=403)
        code = main(["--raw-dir", str(tmp_path)])
    assert code == 3
