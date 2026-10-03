# Disposable virtual desktop for agent computer use. Run it only through
# cellforge.world (offline, read-only root, no capabilities, resource limits).
FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        xvfb xdotool imagemagick xterm openbox x11-utils \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 agent

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 755 /usr/local/bin/entrypoint.sh

USER agent
ENV DISPLAY=:99 HOME=/home/agent
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
