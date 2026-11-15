FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=America/Argentina/Buenos_Aires \
    SIFO_PRODUCCION=1 \
    SIFO_DATA_DIR=/data/salida \
    SIFO_CACHE_DIR=/data/cache \
    SIFO_DB=/data/sifo.db \
    PORT=8000

# Chromium: generación del informe en PDF. tzdata: hora local argentina.
RUN apt-get update \
    && apt-get install -y --no-install-recommends chromium fonts-dejavu-core tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN useradd --create-home --uid 1000 sifo \
    && mkdir -p /data && chown -R sifo:sifo /data /app
USER sifo

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request,os;urllib.request.urlopen('http://127.0.0.1:'+os.environ['PORT']+'/healthz')"

# 1 worker (los intentos de login se cuentan en memoria) con varios hilos;
# timeout alto porque el análisis consulta APIs externas y genera PDF.
CMD exec gunicorn app:app --bind 0.0.0.0:${PORT} --workers 1 --threads 8 --timeout 180 \
    --access-logfile - --forwarded-allow-ips='*'
