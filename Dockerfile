FROM ghcr.io/astral-sh/uv:python3.13-alpine AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

ENV UV_PYTHON_DOWNLOADS=0

RUN apk add git

RUN python3 -V

WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev


FROM python:3.13-alpine

# Keep the base image packages patched
RUN apk upgrade --no-cache

# Non-root runtime user
RUN addgroup -g 1000 nonroot \
    && adduser -D -u 1000 -G nonroot nonroot

COPY --from=builder --chown=nonroot:nonroot /app /app

# pip and setuptools are only needed at build time; dropping them removes their vendored dependencies
RUN rm -rf /usr/local/lib/python3.*/site-packages/pip \
           /usr/local/lib/python3.*/site-packages/pip-*.dist-info \
           /usr/local/lib/python3.*/site-packages/setuptools \
           /usr/local/lib/python3.*/site-packages/setuptools-*.dist-info \
           /usr/local/lib/python3.*/site-packages/pkg_resources \
           /usr/local/bin/pip*

ENV PATH="/app/.venv/bin:$PATH"

ENV PYTHONUNBUFFERED=1

WORKDIR /app

USER nonroot

EXPOSE 8080

CMD ["python3", "-u", "main.py"]
