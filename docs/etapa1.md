# Etapa 1 — inventario, ZIPs oficiales y estimación de API (2026-11-16)

## Acceso
- `robots.txt` → 200 (confirma Crawl-delay 10, Disallow `/wp-content/themes/` y `/wp-content/plugins/`).
- `/ejecuciones-presupuestarias/` → **403 CloudFront** con el User-Agent `gastos-abiertos-cba`. Se paró (ver `logs/etapa1-sonda.log`).
- Los ZIP los bajó el usuario a mano a `data/raw/zips/`. **Sonda a la API: NO realizada** (Disallow + 403 en el sitio). Reintento único del catálogo: pendiente, ~2 h después, mismo UA.
- Un reintento ≠ evasión: no se cambia el UA.

## ZIPs ingeridos (11 archivos; 10 con XLSX)
Cortes trimestrales Mar/Jun/Sep/Dic 2024, Mar/Jun/Sep 2025, Dic 2025 (Cuenta de Inversión), Mar/Jun 2026. El ZIP "Cuenta-de-Inversion-2025-comprimido" trae solo un PDF (no se ingiere). Cada ZIP: Gastos AC, Gastos EMAEE, Recursos AC, Recursos EMAEE.
Cobertura de ejercicios: **2024 y 2025 completos + 2026 hasta junio**. No hay 2015–2023 en ZIPs (la referencia Shiny llega a 2015; solo podría venir de la API, que ofrece 2010–2026).

## Resultado de ingesta
12 870 filas de gastos en la base (todos los cortes; `data/processed/`), 1 855 de recursos. Marzo 2026 coincide con el relevo: 1025 filas AC, 20 jurisdicciones, 32 unidades, 314 programas, 13 partidas; EMAEE 245 filas, 23 entes.
Validación: 80 controles (Σ presupuesto/compromiso/devengado/pagado por archivo, fuente vs DuckDB), 0 fallidos (tolerancia 1 peso). Sin claves duplicadas ni devengados negativos.
Diferencias con el relevo / hallazgos:
- Los XLSX traen ~5 800 filas de hoja con filas vacías al final; las filas reales son ~1 000 (el relevo está bien).
- Nombres de archivo de 2026 vienen con mojibake ("Administraciвn"); se clasifica por prefijo.
- Nombres de jurisdicción/unidad cambian entre años (p. ej. "S.E.M."): se normaliza por código; 1 código de jurisdicción AC con más de un nombre entre años.
- Valores con decimales largos (p. ej. 1264764626.558386): se redondea a centavos para almacenar y se valida contra la suma sin redondear.
- Compromiso solo en AC; EMAEE queda NULL.

## Estimación de requests de la API (por ejercicio, SIN medir)
Cada request cuesta ≥10 s (Crawl-delay): 1 000 requests ≈ 2,8 h.
- Catálogo: 1 vigencias + 1 jurisdicciones + ~31 unidades + ~309 programas (uno por unidad/programa) + ~309 partidas por programa ≈ **650 requests ≈ 1,8 h** (cifras de 2025 desde el agregado).
- Listado de devengados: ≥ 1 POST por (programa, objeto de gasto). Hay ~1 030 pares (programa, partida principal) y por cada uno varios objetos: **~1 000–5 000 requests (3–14 h)** más paginación a 10 por página (N/10).
- Detalle: **2 requests por comprobante** (GetXDevengado + GetDevengadosDet). Si un ejercicio tiene del orden de 10⁴–10⁵ comprobantes (desconocido) son **20 000–200 000 requests = 2–23 días**.
Conclusión: un ejercicio completo de comprobantes es **inviable** con delay de 10 s sin acotar. Solo se puede con un recorte (una jurisdicción / un programa o un objeto de gasto) y N medido por una sonda.

## Recomendación
Empezar por **2025** (último ejercicio cerrado: Cuenta de Inversión Dic-2025 como base de validación estable; 2026 es un blanco móvil) y acotar a **una jurisdicción chica**: candidatas del agregado 2025 con pocos programas: 190 Ministerio de Cooperativas y Mutuales (2 programas), 500 Tribunal de Cuentas (2), 110 Ministerio de Gobierno (3). Orden sugerido de la Etapa 2: (1) sonda de ~10 requests (vigencias → jurisdicciones → 1 programa → 1 POST pageSize=100 → 1 comprobante) para medir N; (2) decidir recorte con ese N.
Alternativa sin la API: la visualización v1 puede salir solo con los ZIP (jurisdicción/unidad/programa/partida, sin CUIT).
