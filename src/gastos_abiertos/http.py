"""Cliente HTTP cortés con cache en disco, delay y backoff.

Diseñado para el único acceso automático permitido en v1: catálogo/descargas de
ZIPs oficiales del Portal de Transparencia de Córdoba.
"""
import hashlib
import logging
import os
import time
from pathlib import Path

import requests

DEFAULT_UA = "gastos-abiertos-cba (proyecto civico local; datos publicos del Portal de Transparencia)"
DEFAULT_DELAY = 10.0
DEFAULT_MAX_RETRIES = 3


class BlockedError(Exception):
    """El servidor respondió 403; no se reintenta."""


class HttpClient:
    """Cliente con un solo worker, delay configurable entre requests,
    backoff exponencial ante 429/5xx y caché en disco solo para 200.
    """

    def __init__(
        self,
        *,
        cache_dir=None,
        delay=DEFAULT_DELAY,
        max_retries=DEFAULT_MAX_RETRIES,
        user_agent=DEFAULT_UA,
        log_path=None,
        session=None,
        sleep=None,
        now=None,
    ):
        self.cache_dir = Path(cache_dir) if cache_dir else Path("data") / "cache" / "http"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.delay = float(delay)
        self.max_retries = int(max_retries)
        self.user_agent = user_agent
        self.session = session if session is not None else requests.Session()
        self.sleep = sleep if sleep is not None else time.sleep
        self.now = now if now is not None else time.monotonic
        self._last_request_time = None

        log_path = Path(log_path) if log_path else Path("logs") / "http.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger("gastos_abiertos.http")
        self.logger.setLevel(logging.INFO)
        self.logger.handlers = []
        handler = logging.FileHandler(log_path)
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        self.logger.addHandler(handler)

    def _cache_key(self, url):
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def _cache_path(self, url):
        return self.cache_dir / f"{self._cache_key(url)}.bin"

    def _enforce_delay(self):
        if self._last_request_time is not None:
            elapsed = self.now() - self._last_request_time
            remaining = self.delay - elapsed
            if remaining > 0:
                self.sleep(remaining)
        self._last_request_time = self.now()

    def get(self, url, **kwargs):
        """GET idempotente: usa caché si existe; si no, request con delay y reintentos."""
        cache_path = self._cache_path(url)
        if cache_path.exists():
            return cache_path.read_bytes()

        headers = kwargs.pop("headers", {})
        headers.setdefault("User-Agent", self.user_agent)

        self._enforce_delay()

        attempt = 0
        backoff = self.delay
        while True:
            start = self.now()
            try:
                resp = self.session.get(url, headers=headers, **kwargs)
            except requests.RequestException:
                attempt += 1
                if attempt > self.max_retries:
                    raise
                self.sleep(backoff)
                backoff *= 2
                continue

            duration = self.now() - start
            self.logger.info(f"GET {url} {resp.status_code} {duration:.3f}s {len(resp.content)}b")

            if resp.status_code == 403:
                raise BlockedError(f"403 bloqueado: {url}")

            if resp.status_code == 200:
                self._write_cache(url, resp.content)
                return resp.content

            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                attempt += 1
                if attempt > self.max_retries:
                    resp.raise_for_status()
                self.sleep(backoff)
                backoff *= 2
                continue

            resp.raise_for_status()

    def _write_cache(self, url, content):
        key = self._cache_key(url)
        tmp = self.cache_dir / f".{key}.tmp"
        dest = self.cache_dir / f"{key}.bin"
        tmp.write_bytes(content)
        os.replace(tmp, dest)
