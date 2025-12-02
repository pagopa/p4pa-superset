# syntax=docker/dockerfile:1.4@sha256:9ba7531bd80fb0a858632727cf7a112fbfd19b17e94c4e84ced81e24ef1a0dbc

#
# 🎯 Version Management
#
ARG IMAGE="apachesuperset.docker.scarf.sh/apache/superset"
# using RC version in order to be able to use a context path different from / (SUPERSET_APP_ROOT env var)
ARG IMAGE_VERSION="6.0.0rc3"
ARG IMAGE_SHA="f639b5fd21832e6d012b0bf0c0111c0df33c5b751f6c8952037f1e0b2480e32d"

# 🌍 Timezone Configuration
ARG TZ="Europe/Rome"

#
# 📥 Base Setup Stage
#
FROM ${IMAGE}:${IMAGE_VERSION}@sha256:${IMAGE_SHA} AS base
ARG TZ

USER root

# Set timezone environment variable
ENV TZ=${TZ}

# Install base packages
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y \
        gcc \
        git \
        libpq-dev \
        pkg-config \
        python3-dev \
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
