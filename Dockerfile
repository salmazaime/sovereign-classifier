# ============================================================
# Stage 1: builder -- installs Python dependencies into a venv.
# Contains compilers/headers that the FINAL image must not carry.
# ============================================================
FROM python:3.12-slim AS builder

WORKDIR /build

# build-essential: needed in case any dependency lacks a prebuilt
# wheel for this platform and must compile from source. Most of our
# dependencies (psycopg[binary], Pillow, etc.) ship prebuilt wheels,
# but this is cheap insurance against a platform mismatch breaking
# the build unpredictably.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ============================================================
# Stage 2: runtime -- clean image, only what's needed to RUN the app.
# ============================================================
FROM python:3.12-slim AS runtime

# tesseract-ocr: the actual OS-level OCR engine, per Step 13's
# explicit note that pytesseract (the Python package) is only a
# wrapper -- without this line, image/PDF-OCR content detection
# would silently no-op in every container, exactly the gap flagged
# at the top of this step.
# curl: used by the HEALTHCHECK below to call our own /health route.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user: running as root inside a container is unnecessary
# privilege -- if the app process were ever compromised, root inside
# the container is a meaningfully worse starting position for an
# attacker than an unprivileged user, even though container
# boundaries add their own isolation. Cheap to do, real to skip.
RUN groupadd --system appuser && useradd --system --gid appuser appuser

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY app/ ./app/
COPY config/ ./config/
COPY scripts/ ./scripts/
RUN mkdir -p .sovereign

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
