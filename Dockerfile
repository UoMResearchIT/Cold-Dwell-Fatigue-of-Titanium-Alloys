# Packs a copy of the project with all its dependencies (including Dream3D)
# Entrypoint is set to the CLI, use docker-compose.yaml for the GUI
# Usage:
#   docker buildx build . -t microtexture:latest
#   docker run --rm microtexture:latest --help
#   docker run --rm -v ./my/data:/data microtexture:latest [...] FILE

FROM ubuntu:24.04 AS dream3d

# Install DREAM3D ----
RUN apt-get update && apt-get install -y \
    wget \
    tar \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/dream3d
RUN wget https://dream3d.bluequartz.net/binaries/DREAM3D-6.5.171-Linux-x86_64.tar.gz && \
    tar -xvzf DREAM3D-6.5.171-Linux-x86_64.tar.gz --strip-components=1 && \
    rm DREAM3D-6.5.171-Linux-x86_64.tar.gz

# DREAM3D runtime dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libglib2.0-0 \
    libxrender1 \
    libx11-xcb-dev \
    libxcb-util-dev \
    libxkbcommon-x11-dev \
    && rm -rf /var/lib/apt/lists/*

ENV LD_LIBRARY_PATH=/opt/dream3d/lib
ENV QT_PLUGIN_PATH=/opt/dream3d/Plugins
ENV QT_QPA_PLATFORM_PLUGIN_PATH=/opt/dream3d/Plugins/platforms
ENV XDG_RUNTIME_DIR=/tmp/runtime-root

ENV PATH="/opt/dream3d/bin:${PATH}"

FROM dream3d AS base

# "Install" this project ----
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV HOME=/tmp
ENV UV_CACHE=/tmp/uv_cache

WORKDIR /opt/microtexture
COPY . .

RUN uv sync
ENV PATH="/opt/microtexture/.venv/bin:${PATH}"
RUN mkdir -p /tmp/.cache/matplotlib && chmod a+rw /tmp/.cache/matplotlib

ENV DREAM3D_VERSION="6.5.171"
ENV DREAM3D_PIPELINE_RUNNER="/opt/dream3d/bin/PipelineRunner"
ENV DREAM3D_PIPELINE_TEMPLATE="{microtexture}/templates/PW_{EXT}_routine_v65.j2"

RUN useradd -m microtexture
RUN mkdir /data
RUN chown microtexture:microtexture /data
VOLUME /data

USER microtexture
WORKDIR /data

ENTRYPOINT ["python", "-m", "microtexture"]

FROM base AS gui
USER root
WORKDIR /opt/microtexture

RUN apt-get update && apt-get install -y \
    python3-tk \
    && rm -rf /var/lib/apt/lists/*
RUN uv sync --group gui

USER microtexture
WORKDIR /data

CMD ["gui"]

FROM base AS final
CMD ["-h"]
