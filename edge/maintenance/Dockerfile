# =============================================================================
#  Nodo Edge de Mantenimiento
# =============================================================================

# --- Etapa 1: construir el entorno virtual con uv ---------------------------------
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.9.17 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

COPY uv.lock pyproject.toml ./
COPY common/pyproject.toml common/pyproject.toml
COPY maintenance/pyproject.toml maintenance/pyproject.toml
RUN uv sync --frozen --no-dev --package maintenance --no-install-workspace

COPY common common
COPY maintenance maintenance
RUN uv sync --frozen --no-dev --package maintenance --no-editable

# --- Etapa 2: imagen final, mínima y sin root ---------------------------------------
FROM python:3.12-slim

RUN useradd --create-home --uid 10001 edge
WORKDIR /app

COPY --from=builder --chown=edge /app/.venv /app/.venv
COPY --chown=edge maintenance/datasets /app/datasets

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    DATASET_PATH=/app/datasets/ai4i2020.csv

USER edge

CMD ["maintenance"]