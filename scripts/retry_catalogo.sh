#!/bin/bash
# Reintento UNICO del catálogo a las 16:30 locales, mismo UA, sin mail. No reintenta si falla.
cd ~/gastos-abiertos-cba
T=$(date -d "today 16:30" +%s); N=$(date +%s)
[ $T -gt $N ] && sleep $((T-N))
UA="gastos-abiertos-cba (proyecto civico local; datos publicos del Portal de Transparencia)"
mkdir -p data/raw/pages
C=$(curl -sS -A "$UA" -o data/raw/pages/ejecuciones_retry.html -w "%{http_code}" https://transparencia.cba.gov.ar/ejecuciones-presupuestarias/)
echo "$(date -Is) GET /ejecuciones-presupuestarias/ (reintento unico, UA sin mail) -> $C" | tee -a logs/etapa1-sonda.log
