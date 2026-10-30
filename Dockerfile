# syntax=docker/dockerfile:1.4@sha256:9ba7531bd80fb0a858632727cf7a112fbfd19b17e94c4e84ced81e24ef1a0dbc

#
# 🎯 Version Management
#
#  Using superset PagoPA custom version with correct italian transalations
ARG IMAGE="ghcr.io/pagopa/superset"
ARG IMAGE_VERSION="6.1.0_v1.0.1"
ARG IMAGE_SHA="225c4c200214aff13ad916fe52d1580c4a8fb90dab33497afdb8a0790c40e756"

# 🌍 Timezone Configuration
ARG TZ="Europe/Rome"

#
# 📥 Base Setup Stage
#
FROM ${IMAGE}@sha256:${IMAGE_SHA} AS base
ARG TZ

USER root

# Set timezone environment variable
ENV TZ=${TZ}

# Install base packages
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        gcc \
        git \
        tini \
        # Configure timezone + ENV=TZ \
        tzdata && \
    apt-get clean

WORKDIR /build

# Copy build configuration
COPY .git .git

# Storing source git branch details
RUN git show --summary > build.info && \
    chown -R superset:superset /build && \
    chmod -R 775 /build && \
    apt-get remove -y git

#
# 📦 Dependency Setup Stage
#
FROM base AS dependencies

# Install dependencies
RUN uv pip install \
    authlib \
    psycopg2-binary \
    requests \
    pyjwt

#
# 🏗️ Build Stage
#
FROM dependencies AS build

# Copy configs
COPY --chown=superset:superset src/configs /app/configs

# Copy static assets
COPY --chown=superset:superset src/static /app/superset/static

#
# 🚀 Runtime Stage
#
FROM build AS runtime

WORKDIR /app

# 🔌 Container Configuration
USER superset