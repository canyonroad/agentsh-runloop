FROM ubuntu:24.04

ARG AGENTSH_REPO=canyonroad/agentsh
ARG AGENTSH_TAG=v0.8.10
ARG DEB_ARCH=amd64

# Install base dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        bash \
        git \
        sudo \
        libseccomp2 \
    && rm -rf /var/lib/apt/lists/*

# Download and install agentsh
RUN set -eux; \
    version="${AGENTSH_TAG#v}"; \
    deb="agentsh_${version}_linux_${DEB_ARCH}.deb"; \
    url="https://github.com/${AGENTSH_REPO}/releases/download/${AGENTSH_TAG}/${deb}"; \
    echo "Downloading: ${url}"; \
    curl -fsSL -L "${url}" -o /tmp/agentsh.deb; \
    dpkg -i /tmp/agentsh.deb; \
    rm -f /tmp/agentsh.deb; \
    agentsh --version

# Create agentsh directories (world-writable for Runloop's user)
RUN mkdir -p /etc/agentsh/policies \
    /var/lib/agentsh/quarantine \
    /var/lib/agentsh/sessions \
    /var/log/agentsh && \
    chmod 777 /etc/agentsh /etc/agentsh/policies && \
    chmod 777 /var/lib/agentsh /var/lib/agentsh/quarantine /var/lib/agentsh/sessions && \
    chmod 777 /var/log/agentsh

# Create a non-root user
RUN useradd -m -s /bin/bash runloop && \
    echo "runloop ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    chown -R runloop:runloop /var/lib/agentsh /var/log/agentsh

# NOTE: Shell shim is installed at runtime via launch_commands, not here.
# Installing during build would cause Runloop's post-build commands to fail
# because agentsh would intercept them before config files are mounted.

# Configure agentsh for runtime
ENV AGENTSH_SERVER=http://127.0.0.1:18080

USER runloop
WORKDIR /home/runloop

CMD ["/bin/bash"]
