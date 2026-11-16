# gastos-abiertos-cba
Scraper respetuoso y visualización estática de los gastos públicos de la Provincia de Córdoba. Inspirado en https://bsaenz.shinyapps.io/pauta-cordoba/ (pauta publicitaria), pero para todos los gastos. Proyecto cívico local: **no se publica ni se despliega**.

**Estado: v1 completa (Etapa 4), solo local, sin publicar.** ZIPs oficiales ingeridos (2024–jun 2026) desde descarga manual; la API no se usa (decisión del 2026-11-16).

## Fuentes
- A) ZIPs oficiales de ejecución presupuestaria: https://transparencia.cba.gov.ar/ejecuciones-presupuestarias/ (Administración Central y EMAEE; acumulados, sin objeto 3090000, CUIT, comprobante ni proveedor).
- B) API JSON `jurisdiccionesApi.php` (microdato/comprobantes). robots.txt: Crawl-delay 10 y Disallow `/wp-content/themes/` → uso mínimo, solo con aprobación.
- Relevo verificado el 2026-11-16; endpoints a reconfirmar con sonda corta. Si algo no coincide, se prioriza lo verificado y se anota acá.

## Límites
Se muestra CUIT, no razón social (el portal desde jul-2026 no la entrega; no se adivina ni se usan padrones externos). Los ZIP son acumulados: no se suman cortes. Excluyen partidas 20 (y 21 en AC). Fuera de v1: transferencias a municipios y ejecución por ubicación geográfica. Opcional luego: filtro 3090000 y ajuste por inflación.

## Correr
`uv venv && uv pip install -r requirements.txt && python -m pytest` · CLI: `inventory`, `download-official`, `ingest-official`, `crawl-api --ejercicio YYYY [--jurisdiccion X --limit N --dry-run]`.

## Docs
`docs/schema.sql`, `docs/validacion.md`, `docs/plan-recoleccion.md`.

## Atribución
Datos: Portal de Transparencia de la Provincia de Córdoba (transparencia.cba.gov.ar).

## Web (Etapa 3)
`PYTHONPATH=src python -m gastos_abiertos.export_web` genera `web/data/*.json` desde DuckDB; luego `python3 -m http.server -d web 8000` y abrir http://localhost:8000/. HTML/CSS/JS plano, sin CDN. v1 usa solo ZIP oficiales: sin CUIT, proveedor ni comprobantes (decisión del 2026-11-16: sin API).

## Cómo correr (completo)
1. `uv venv .venv && uv pip install -r requirements.txt --python .venv/bin/python`
2. Poner los ZIP oficiales en `data/raw/zips/` (el sitio dio 403 a requests automáticos; `download-official` existe pero solo se probó con mocks).
3. `PYTHONPATH=src .venv/bin/python -m gastos_abiertos.cli ingest-official` → `data/processed/` (DuckDB, Parquet, CSV, `validacion.json`).
4. `PYTHONPATH=src .venv/bin/python -m gastos_abiertos.export_web` y `python3 -m http.server -d web 8000`.
5. Tests: `.venv/bin/python -m pytest -q` (25, sin red).

## Estado de cada comando
`inventory`, `ingest-official`: funcionan. `download-official`: implementado, solo con mocks (User-Agent identificable, sin mail; delay 10 s; para ante 403, exit 3). `crawl-api`: **no implementado** (v1 sin API).

## Validación y desvíos
Ver `docs/desvios.md`: 80 controles XLSX vs base sin desvíos; 96 de 16 202 pares de acumulados bajan entre cortes (reportados, no corregidos). Los montos de la web se suman en centavos enteros (BigInt).

## Pendientes / fuera de v1
- Microdato por proveedor/CUIT, comprobantes y filtro 3090000 "Publicidad y Propaganda": requieren la API (bajo Disallow, 403 en el sitio) o un pedido formal al portal (Ley 8803). Datos personales: los CUIT de personas físicas (Ley 25.326) exigen decisión antes de mostrarlos.
- Años 2015–2023 (solo disponibles por API).
- Ajuste por inflación (fuente a documentar); ARS constantes.
- Transferencias a municipios y ejecución por ubicación geográfica.
- Web: sin probar con lector de pantalla ni en otros navegadores; contraste sin medir.
- Esquema `docs/schema.sql` incluye tablas de microdato (`hecho_devengado*`) vacías, reservadas para una versión con API.

## Datos y licencia
- Los datos son **públicos y agregados** (ejecución presupuestaria por jurisdicción, unidad, programa y partida). No incluyen CUIT, proveedores ni comprobantes ni datos personales.
- Fuente: Portal de Transparencia de la Provincia de Córdoba. ZIPs oficiales en https://transparencia.cba.gov.ar/ejecuciones-presupuestarias/ (los datos pertenecen a su fuente; este repo no es un sitio oficial).
- Los ZIP originales no se incluyen en el repo (`data/raw/`); se bajan de la página anterior y se dejan en `data/raw/zips/`.
- Regenerar la base: `ingest-official` (paso 3 de "Cómo correr") reconstruye `data/processed/` (Parquet/CSV; el archivo DuckDB no se versiona). Luego `export_web` regenera `web/data/`.
- Ver la web: `python3 -m http.server -d web 8000` y abrir http://localhost:8000/.
- Licencia del código: MIT (`LICENSE`). Los datos conservan los términos de la fuente.
