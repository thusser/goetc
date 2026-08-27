FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
WORKDIR /goetc
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
COPY . /goetc/
CMD ["/goetc/.venv/bin/gunicorn", "--bind", "0.0.0.0:9300", "--worker-tmp-dir", "/dev/shm", "--workers=2", "--threads=4", "--worker-class=gthread", "goetc.web:app"]
