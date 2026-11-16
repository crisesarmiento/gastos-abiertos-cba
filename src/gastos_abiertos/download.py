"""Descarga idempotente y reanudable de ZIPs oficiales desde el catálogo."""
import argparse
import logging
import sys
from pathlib import Path

from . import inventory
from .http import BlockedError, HttpClient

logger = logging.getLogger("gastos_abiertos.download")

DEFAULT_CATALOG_URL = "https://transparencia.cba.gov.ar/ejecuciones-presupuestarias/"


def _missing_zips(catalog_html, zips_dir, limit=None):
    """Devuelve [(url, dest_path)] de los ZIPs que faltan localmente."""
    urls = inventory.parse_catalog(catalog_html.decode("utf-8", errors="replace"))
    to_download = []
    for url in urls:
        name = url.rsplit("/", 1)[-1]
        dest = zips_dir / name
        if dest.exists() and dest.stat().st_size > 0:
            continue
        to_download.append((url, dest))
        if limit is not None and len(to_download) >= limit:
            break
    return to_download


def download_official(
    catalog_url=DEFAULT_CATALOG_URL,
    raw_dir="data/raw",
    *,
    dry_run=False,
    limit=None,
    client=None,
):
    """Baja el catálogo una vez y luego los ZIPs faltantes.

    - Idempotente: archivos existentes con tamaño > 0 se saltan.
    - Reanudable: escribe a ``.part`` y renombra al final.
    - ``dry_run=True`` lista lo que bajaría sin descargar ZIPs.
    - Ante ``BlockedError`` se propaga sin más requests.
    """
    raw_dir = Path(raw_dir)
    zips_dir = raw_dir / "zips"
    pages_dir = raw_dir / "pages"
    zips_dir.mkdir(parents=True, exist_ok=True)
    pages_dir.mkdir(parents=True, exist_ok=True)

    client = client if client is not None else HttpClient()

    try:
        catalog_html = client.get(catalog_url)
    except BlockedError as exc:
        logger.error("Bloqueado al bajar el catálogo: %s", exc)
        raise

    catalog_path = pages_dir / "ejecuciones.html"
    catalog_path.write_bytes(catalog_html)

    to_download = _missing_zips(catalog_html, zips_dir, limit=limit)

    if dry_run:
        return to_download

    downloaded = []
    for url, dest in to_download:
        part = dest.with_suffix(dest.suffix + ".part")
        try:
            data = client.get(url)
        except BlockedError as exc:
            logger.error("Bloqueado al bajar %s: %s", url, exc)
            raise
        part.write_bytes(data)
        part.rename(dest)
        downloaded.append(dest)

    return downloaded


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(prog="gastos-abiertos download-official")
    p.add_argument("--catalog-url", default=DEFAULT_CATALOG_URL)
    p.add_argument("--raw-dir", default="data/raw")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int)
    args = p.parse_args(argv)

    try:
        result = download_official(
            args.catalog_url,
            raw_dir=args.raw_dir,
            dry_run=args.dry_run,
            limit=args.limit,
        )
    except BlockedError as exc:
        print(f"BLOQUEADO: {exc}", file=sys.stderr)
        return 3

    if args.dry_run:
        print(f"dry-run: faltarían {len(result)} ZIPs")
        for url, dest in result:
            print(f"  {url} -> {dest}")
    else:
        print(f"descargados: {len(result)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
