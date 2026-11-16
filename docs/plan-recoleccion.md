# Plan de recolección (a revisar por @oracle antes de cualquier crawl)
- Prioridad: ZIPs oficiales (sin Disallow). API `/wp-content/themes/` está **Disallow** en robots.txt: uso mínimo y solo con ok explícito.
- Un worker, delay ≥10 s (Crawl-delay), backoff exponencial ante 429/5xx, parar ante 403. UA `gastos-abiertos-cba`.
- Caché en disco por URL+body (hash), reanudable e idempotente; log con timestamp, endpoint, status, duración, ítems.
- Estimación por ejercicio y año recomendado: se calcula en Etapa 1 (sonda mínima).

## Revisión @oracle (Etapa 1, 2026-11-16) — condiciones antes de la Etapa 2
1. Reintento único del catálogo (mismo UA). Si da 403 → vía API cerrada; v1 solo con ZIPs.
2. Ok explícito y escrito del usuario para usar la API bajo Disallow, con tope duro (≤ 50 requests en la Etapa 2) y cortes: cualquier 403, 2 errores 5xx seguidos, o HTML donde se espera JSON.
3. Contactar al portal / pedido de acceso a la información (Ley 8803) para obtener el microdato; el UA con contacto lo decide el usuario.
4. Recorte: jurisdicción chica **y** partida distinta de Personal (Personal no suele traer CUIT/comprobantes). Fijar umbral de desvío microdato vs agregado, mapeo objeto→partida principal, manejo de desafectaciones (negativos) y corte de comparación (Cuenta de Inversión Dic-2025).
5. Caché: normalizar body antes de hashear, cachear solo 200 con JSON válido, escritura atómica; clave (ejercicio, id_devengado); invalidar listado si cambia totalElements.
6. Probar caché y reanudación sin red (mocks) antes del primer request real.
7. Privacidad: CUIT de personas físicas son dato personal (Ley 25.326); decidir antes de mostrarlos en la web.
8. La estimación de requests no está medida; "~309 partidas por programa" puede ser mucho menos si un request devuelve todas.
