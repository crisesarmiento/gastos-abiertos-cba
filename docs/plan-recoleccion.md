# Plan de recolección (a revisar por @oracle antes de cualquier crawl)
- Prioridad: ZIPs oficiales (sin Disallow). API `/wp-content/themes/` está **Disallow** en robots.txt: uso mínimo y solo con ok explícito.
- Un worker, delay ≥10 s (Crawl-delay), backoff exponencial ante 429/5xx, parar ante 403. UA `gastos-abiertos-cba`.
- Caché en disco por URL+body (hash), reanudable e idempotente; log con timestamp, endpoint, status, duración, ítems.
- Estimación por ejercicio y año recomendado: se calcula en Etapa 1 (sonda mínima).
