"""Inventario de ZIPs oficiales: locales (data/raw/zips) y, si existe, el catálogo HTML guardado."""
import re
from pathlib import Path
from bs4 import BeautifulSoup

def parse_catalog(html):
    soup = BeautifulSoup(html, "html.parser")
    return sorted({a["href"] for a in soup.find_all("a", href=True) if a["href"].lower().endswith(".zip")})

def inventory(raw_dir="data/raw"):
    raw = Path(raw_dir)
    cat = raw / "pages" / "ejecuciones.html"
    remote = []
    if cat.exists() and b"<TITLE>ERROR" not in cat.read_bytes()[:400]:
        remote = parse_catalog(cat.read_text(errors="replace"))
    local = sorted(p.name for p in (raw / "zips").glob("*.zip"))
    return {"remote": remote, "local": local, "faltan_local": [u for u in remote if u.rsplit("/", 1)[-1] not in local]}
