# Plan de validación
1. **XLSX vs base**: por archivo y columna (presupuesto, compromiso, devengado, pagado), suma de filas del XLSX == suma en `hecho_agregado` (tolerancia ≤ 1 peso). Falla = corrida inválida.
2. **Acumulados**: nunca sumar cortes distintos del mismo ejercicio; la vista usa el último `fecha_corte` por (tipo, ejercicio).
3. **Microdato vs agregado**: para un mismo recorte (ejercicio, jurisdicción, programa, partida) comparar Σ devengado de `hecho_devengado` con `hecho_agregado.devengado`. Se reporta el desvío (abs y %) en `docs/desvios.md`; jamás se corrige en silencio.
4. **Normalización**: CUIT = 11 dígitos (si no, queda NULL y se loguea); montos Decimal; fechas ISO; jurisdicción por código numérico.
5. **Crawl**: contador de requests, páginas esperadas (totalPages) vs recibidas, reanudación sin duplicados (clave id_devengado).
