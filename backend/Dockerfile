FROM python:3.12-slim

# ── Dépendances système ────────────────────────────────────────────────────────
# WeasyPrint nécessite : pango, cairo, gdk-pixbuf, fontconfig
# Pillow nécessite : zlib, libjpeg, libpng
RUN apt-get update && apt-get install -y --no-install-recommends \
    # WeasyPrint — rendu HTML/CSS → PDF (Debian bookworm)
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libcairo-gobject2 \
    libgdk-pixbuf-2.0-0 \
    libharfbuzz0b \
    libfontconfig1 \
    libffi8 \
    libglib2.0-0 \
    libxml2 \
    libxslt1.1 \
    zlib1g \
    libjpeg62-turbo \
    libpng16-16 \
    libssl3 \
    # Polices pour génération PDF (Unicode complet requis pour UEMOA)
    fonts-liberation \
    fonts-dejavu-core \
    fonts-noto \
    fonts-noto-extra \
    # Cache MIME et outils
    shared-mime-info \
    curl \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONPATH=/app

# ── Dépendances Python ─────────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Validation WeasyPrint au build : import + génération PDF réelle ────────────
RUN python -c "\
from weasyprint import HTML; \
pdf = HTML(string='<html><body><h1>Fiissa Test</h1><p>WeasyPrint OK</p></body></html>').write_pdf(); \
assert len(pdf) > 1000, f'PDF trop petit: {len(pdf)} bytes'; \
print(f'[WeasyPrint] PDF generation OK ({len(pdf)} bytes)')"

# ── Code applicatif ────────────────────────────────────────────────────────────
COPY . .

# ── Utilisateur non-root (sécurité — CIS Docker Benchmark 4.1) ────────────────
RUN groupadd -r appuser && useradd -r -g appuser -s /sbin/nologin appuser

# ── Répertoires media avec ownership correct ───────────────────────────────────
RUN mkdir -p /app/media/receipts /app/media/products /app/media/temp \
             /app/celerybeat-data \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
