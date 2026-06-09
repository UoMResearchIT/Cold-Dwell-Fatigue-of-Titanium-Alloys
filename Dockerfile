# Packs a copy of the project with all its dependencies (including Dream3D)
# Entrypoint is set to the CLI, use docker-compose.yaml for the GUI
# Usage:
#   docker buildx build . -t microtexture:simplnx
#   docker run --rm microtexture:simplnx --help
#   docker run --rm -v ./my/data:/data microtexture:simplnx [...] FILE

FROM ghcr.io/prefix-dev/pixi:0.40.0 AS build

COPY . /opt/microtexture
WORKDIR /opt/microtexture
RUN pixi install && pixi run setup-plugins

# Create a shell-hook script to activate the environment
# and run the command passed to the container
RUN pixi shell-hook > /shell-hook.sh
RUN echo 'exec "$@"' >> /shell-hook.sh

FROM ghcr.io/uomresearchit/dream3d:6.5.171 AS base

COPY --from=build /opt/microtexture/.pixi/envs /opt/microtexture/.pixi/envs
COPY --from=build /shell-hook.sh /shell-hook.sh
WORKDIR /opt/microtexture

# ENV HOME=/tmp
# RUN mkdir -p /tmp/.cache/matplotlib && chmod a+rw /tmp/.cache/matplotlib

RUN useradd -m microtexture
RUN mkdir /data
RUN chown microtexture:microtexture /data
VOLUME /data

USER microtexture
WORKDIR /data

ENTRYPOINT ["/bin/bash", "/shell-hook.sh", "microtexture"]

FROM base AS test
USER root
RUN apt-get update && apt-get install -y docker.io && rm -rf /var/lib/apt/lists/*

FROM base AS final

CMD ["-h"]
