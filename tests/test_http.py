import pytest
import requests
import responses

from gastos_abiertos.http import BlockedError, DEFAULT_UA, HttpClient


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
def tmp_http(tmp_path):
    """Cliente con cache, reloj y sleep inyectados; sin requests reales."""
    clock = FakeClock()
    session = requests.Session()
    client = HttpClient(
        cache_dir=tmp_path / "cache",
        delay=10.0,
        log_path=tmp_path / "http.log",
        session=session,
        sleep=clock.sleep,
        now=clock.now,
    )
    return client, clock


@responses.activate
def test_403_raises_blocked_no_retry(tmp_http):
    client, clock = tmp_http
    url = "https://example.com/file.zip"
    responses.add(responses.GET, url, status=403, body=b"blocked")

    with pytest.raises(BlockedError):
        client.get(url)

    assert len(responses.calls) == 1
    assert clock.sleeps == []


@responses.activate
def test_429_500_backoff_then_success(tmp_http):
    client, clock = tmp_http
    url = "https://example.com/file.zip"
    responses.add(responses.GET, url, status=429)
    responses.add(responses.GET, url, status=500)
    responses.add(responses.GET, url, status=200, body=b"ok")

    data = client.get(url)
    assert data == b"ok"
    assert len(responses.calls) == 3
    # backoff: delay=10, luego 20
    assert clock.sleeps == [10.0, 20.0]


@responses.activate
def test_429_exhausts_retries_then_raises(tmp_http):
    client, clock = tmp_http
    url = "https://example.com/file.zip"
    for _ in range(4):  # intento inicial + 3 reintentos
        responses.add(responses.GET, url, status=429)

    with pytest.raises(requests.HTTPError):
        client.get(url)

    assert len(responses.calls) == 4
    assert clock.sleeps == [10.0, 20.0, 40.0]


@responses.activate
def test_cache_hit_avoids_request(tmp_http):
    client, clock = tmp_http
    url = "https://example.com/file.zip"
    responses.add(responses.GET, url, status=200, body=b"payload")

    assert client.get(url) == b"payload"
    assert len(responses.calls) == 1

    # segunda llamada: cache hit, no hace request
    assert client.get(url) == b"payload"
    assert len(responses.calls) == 1
    assert clock.sleeps == []  # tampoco espera


@responses.activate
def test_delay_respected_between_requests(tmp_http):
    client, clock = tmp_http
    url1 = "https://example.com/a.zip"
    url2 = "https://example.com/b.zip"
    responses.add(responses.GET, url1, status=200, body=b"a")
    responses.add(responses.GET, url2, status=200, body=b"b")

    client.get(url1)
    client.get(url2)

    assert len(responses.calls) == 2
    assert clock.sleeps == [10.0]


@responses.activate
def test_user_agent_exact(tmp_http):
    client, _ = tmp_http
    url = "https://example.com/file.zip"
    responses.add(responses.GET, url, status=200, body=b"x")

    client.get(url)

    req = responses.calls[0].request
    assert req.headers["User-Agent"] == DEFAULT_UA
