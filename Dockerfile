# Packs a copy of the project with all its dependencies (including Dream3D)
# Entrypoint is set to the CLI, use docker-compose.yaml for the GUI
# Usage:
#   docker buildx build . -t microtexture:latest
#   docker run --rm microtexture:latest --help
#   docker run --rm -v ./my/data:/data microtexture:latest [...] FILE

# PROVISIONAL: The DREAM3D tarball is no longer available for download, so we're building on the
# last working image while we migrate to SIMPLNX. See Dockerfile.v0.3.0 for the original version.

FROM ghcr.io/uomresearchit/cold-dwell-fatigue-of-titanium-alloys:v0.3.0-cli AS base

RUN rm -rf /opt/microtexture
COPY . /opt/microtexture
WORKDIR /opt/microtexture
RUN uv sync

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
