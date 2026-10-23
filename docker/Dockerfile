FROM ghcr.io/jdx/mise:2026.10.11-debian AS base

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends gettext \
    && rm -rf /var/lib/apt/lists/*

ENV DJANGO_SETTINGS_MODULE=lapidarium.edges.settings
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=src
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml poetry.lock README.md docker/mise.toml docker/mise.lock /app/
COPY docker/.mise /app/.mise

RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p staticfiles media \
    && chown -R appuser:appuser /app /mise

# hadolint ignore=DL3066
USER appuser

RUN mise trust && mise install --locked

FROM base AS prod

RUN mise exec -- poetry install --only main --no-root

COPY --chown=appuser:appuser src ./src

# Catalogs compile here: .mo files are build output and stay out of git.
RUN find src -name django.po -execdir msgfmt --check -o django.mo django.po \;

EXPOSE 8000

# prod-start runs migrate + collectstatic, then gunicorn (docker/mise.toml).
CMD ["mise", "run", "prod-start"]
