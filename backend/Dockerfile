# Runtime — distroless ubuntu/python: ни shell, ни утилит.
# Команды Django: docker compose run --rm backend <команда>, например createsuperuser.
# PID 1 и сигналы — `init: true` в compose (tini из Docker).
# Пользователь — _daemon_ (584792) из самого образа: с ним Celery не считает себя root.

ARG PYTHON_VERSION=3.14
ARG UBUNTU_VERSION=26.04_stable
ARG UV_VERSION=0.11.24

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# --- builder: зависимости, статика, байткод ---
FROM python:${PYTHON_VERSION}-slim-trixie AS builder

ARG PYTHON_VERSION

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/.venv

COPY --from=uv /uv /usr/local/bin/uv

WORKDIR /build
COPY pyproject.toml uv.lock ./
# Только основные зависимости: без групп dev и test
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-default-groups --no-install-project

RUN ln -s "/.venv/lib/python${PYTHON_VERSION}/site-packages" /site-packages

COPY src /src
RUN mkdir -p /src/static /src/media /src/private \
    && BUILD_MODE=1 /.venv/bin/python /src/manage.py collectstatic --noinput \
    && /.venv/bin/python -m compileall -q /src \
    && chown -R 584792:584792 /src/media /src/private

# --- runtime ---
FROM ubuntu/python:${PYTHON_VERSION}-${UBUNTU_VERSION} AS runtime

ARG PYTHON_VERSION
ARG VERSION=0.0.0

LABEL org.opencontainers.image.title="art-teplo backend" \
      org.opencontainers.image.source="https://github.com/art-teplo/site"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONNOUSERSITE=1 \
    PYTHONPATH="/site-packages:/src" \
    BACKEND__VERSION="${VERSION}"

# Код и зависимости принадлежат root: процесс их только читает.
# Писать может лишь в /src/media и /src/private (chown в builder): локальные
# файлы, пока S3 выключен; private — файлы заявок, наружу не отдаются
COPY --from=builder /.venv/lib/python${PYTHON_VERSION}/site-packages /site-packages
COPY --from=builder /src /src

# WORKDIR после COPY: иначе каталог создаётся от USER базового образа (_daemon_)
WORKDIR /src

USER 584792:584792

EXPOSE 8000

ENTRYPOINT ["python3", "/src/manage.py"]
CMD ["startservice"]
