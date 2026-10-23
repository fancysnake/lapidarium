# mise on debian-slim, linux/amd64. Projects pin their toolchain in their own
# mise.toml and run `mise install` on top of this.

FROM debian:trixie-slim

ARG MISE_VERSION=2026.9.0

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /mise

ADD --checksum=sha256:c9b089f2be1db4d4262eacaf367e480e7a328848adcc37d9d1612996902485d0 --chmod=755 \
    https://github.com/jdx/mise/releases/download/v${MISE_VERSION}/mise-v${MISE_VERSION}-linux-x64 \
    /usr/local/bin/mise

ENV MISE_DATA_DIR=/mise
ENV MISE_CONFIG_DIR=/mise
ENV MISE_CACHE_DIR=/mise/cache
ENV PATH=/mise/shims:$PATH

ENTRYPOINT ["mise"]
