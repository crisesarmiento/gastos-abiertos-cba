# Desvíos y hallazgos de datos (v1, solo ZIPs oficiales)

No se hace validación microdato vs agregado: la v1 no usa la API (decisión del 2026-11-16). Ver "Pendientes".

## Validación hecha
- Σ presupuesto/compromiso/devengado/pagado por archivo, XLSX vs base: 80 controles, 0 desvíos (> 1 peso).
- Sin claves duplicadas ni devengados negativos en ningún corte.
- Los acumulados no se suman entre cortes: la vista `v_agregado_ultimo_corte` y la web usan el último corte por (tipo, ejercicio).

## Desvío encontrado: acumulados que bajan entre cortes
Un acumulado de devengado debería no disminuir entre cortes del mismo ejercicio. En 77 de ~16 600 pares (clave: tipo, jurisdicción, unidad, programa, partida, finalidad, función; cortes mar/jun/sep/dic) el valor baja. No se corrigió ni se oculta; se reporta:
| Tipo | Ejercicio | Pares con baja | Monto total de la baja |
|---|---|---|---|
| AC | 2024 | 32 | $ 7 546 598 883 |
| AC | 2025 | 32 | $ 344 092 039 |
| AC | 2026 | 13 | $ 117 457 670 274 |
| EMAEE | 2024 | 9 | $ 75 847 331 |
| EMAEE | 2025 | 9 | $ 97 898 940 |
| EMAEE | 2026 | 1 | $ 949 233 |
Ejemplo mayor: AC 2026, jurisdicción 115 (Agencia Córdoba de Inversión y Financiamiento), programa 084 "Aportes a Agencia...", partida 10: devengado marzo $285 430 035 699,86 → junio $168 209 504 105,05 (−$117 220 531 594,81). Posibles causas (no verificadas): anulaciones/reclasificaciones o cambio de criterio de imputación entre cortes. No se pudo confirmar con la fuente.

## Diferencias con el relevo del 2026-11-16
- Los XLSX tienen ~5 800 filas de hoja con filas vacías al final; las reales son ~1 000 (coincide con el relevo).
- Nombres de archivo de 2026 con mojibake ("Administraciвn"): se clasifica por prefijo.
- Nombres de jurisdicción/unidad cambian entre años (sufijo "S.E.M.", etc.); se normaliza por código.
- El catálogo respondió 403 (CloudFront) al User-Agent identificable; los ZIP se bajaron a mano. Ver `logs/etapa1-sonda.log`.
- Cobertura: 2024, 2025 y 2026 hasta junio. No hay 2015–2023.
- Compromiso en AC es igual a devengado en las filas de AC observadas (viene así de la fuente); EMAEE no trae compromiso.

## Pendientes
Ver README.
