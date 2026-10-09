FROM jdxcode/mise:2026.9@sha256:67514a972b2bddd0eca59b8c4baf4e106fc4e9f9de11233bc2305414bf672ee3 AS base

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends gettext \
    && rm -rf /var/lib/apt/lists/*

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

EXPOSE 8000

# Base image sets ENTRYPOINT ["mise"]; prod-start runs migrate + collectstatic,
# then gunicorn (docker/mise.toml).
CMD ["run", "prod-start"]
