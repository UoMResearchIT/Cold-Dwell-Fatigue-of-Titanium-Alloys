FROM ubuntu:24.04

# Install DREAM3D
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

ENV LD_LIBRARY_PATH=/opt/dream3d/lib:${LD_LIBRARY_PATH}
ENV QT_PLUGIN_PATH=/opt/dream3d/Plugins
ENV QT_QPA_PLATFORM_PLUGIN_PATH=/opt/dream3d/Plugins/platforms
ENV XDG_RUNTIME_DIR=/tmp/runtime-root

