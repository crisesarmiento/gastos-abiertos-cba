# gastos-abiertos-cba
Scraper respetuoso y visualización estática de los gastos públicos de la Provincia de Córdoba. Inspirado en https://bsaenz.shinyapps.io/pauta-cordoba/ (pauta publicitaria), pero para todos los gastos. Proyecto cívico local: **no se publica ni se despliega**.

**Estado: Etapa 0 (diseño).** Sin datos todavía.

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
