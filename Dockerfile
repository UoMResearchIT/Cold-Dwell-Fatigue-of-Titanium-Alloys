# Packs a copy of the project with all its dependencies (including Dream3D)
# Entrypoint is set to the CLI, use docker-compose.yaml for the GUI
# Usage:
#   docker buildx build . -t microtexture:latest
#   docker run --rm microtexture:latest --help
#   docker run --rm -v ./my/data:/data microtexture:latest [...] FILE

FROM ghcr.io/uomresearchit/dream3d:6.5.171 AS base

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
RUN uv sync --extra gui

USER microtexture
WORKDIR /data

CMD ["gui"]

FROM base AS final
CMD ["-h"]
