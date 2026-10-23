FROM debian:trixie-slim AS base

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gettext \
    && rm -rf /var/lib/apt/lists/*

ENV MISE_DATA_DIR=/mise
ENV MISE_CONFIG_DIR=/mise
ENV MISE_CACHE_DIR=/mise/cache
ENV MISE_INSTALL_PATH=/usr/local/bin/mise
ENV MISE_VERSION=v2026.9.0
ENV PATH=/mise/shims:$PATH

RUN curl -fsSL https://mise.run | sh \
    && mkdir -p /mise

ENV DJANGO_SETTINGS_MODULE=lapidarium.edges.settings
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=src
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml poetry.lock README.md docker/mise.toml /app/

RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p staticfiles media \
    && chown -R appuser:appuser /app /mise

# hadolint ignore=DL3066
USER appuser

RUN mise trust && mise install

FROM base AS prod

RUN mise exec -- poetry install --only main --no-root

COPY --chown=appuser:appuser src ./src

# Catalogs compile here: .mo files are build output and stay out of git.
RUN find src -name django.po -execdir msgfmt --check -o django.mo django.po \;

EXPOSE 8000

# prod-start runs migrate + collectstatic, then gunicorn (docker/mise.toml).
ENTRYPOINT ["mise"]
CMD ["run", "prod-start"]
