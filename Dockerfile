# syntax=docker/dockerfile:1.4@sha256:9ba7531bd80fb0a858632727cf7a112fbfd19b17e94c4e84ced81e24ef1a0dbc

#
# 🎯 Version Management
#
ARG IMAGE="apachesuperset.docker.scarf.sh/apache/superset"
ARG IMAGE_VERSION="6.0.0rc2"
ARG IMAGE_SHA="48b837a5fe326422cf6b784e0673ccb65c2ed253e784a0097138d14a0cb25a70"

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

#
# 📦 Dependency Setup Stage
#
FROM base AS dependencies

# Install dependencies
RUN uv pip install \
    psycopg2-binary

WORKDIR /build

# Copy build configuration
COPY .git .git

# Storing source git branch details
RUN git show --summary > build.info && \
    chown -R superset:superset /build && \
    chmod -R 775 /build

#
# 🏗️ Build Stage
#
FROM dependencies AS build

# Copy source code
COPY --chown=superset:superset src /app

#
# 🚀 Runtime Stage
#
FROM build AS runtime

WORKDIR /app

# 🔌 Container Configuration
USER superset
