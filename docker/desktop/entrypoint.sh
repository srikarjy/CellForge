#!/bin/sh
set -eu

# TCP listening is disabled; the display is reachable only inside the container.
Xvfb :99 -screen 0 "${WIDTH:-1280}x${HEIGHT:-800}x24" -nolisten tcp &
openbox >/dev/null 2>&1 &
exec sleep infinity
