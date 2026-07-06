#!/bin/sh
set -e

# Kubernetes forces the container to start as uid 1000 already (podSecurityContext
# .runAsUser), so there's no root available to chown/gosu with — just exec directly.
# Only docker-compose / plain `docker run` (which start as root by default) need
# the chown-then-drop-privileges dance below, to fix root-owned named volumes.
if [ "$(id -u)" != "0" ]; then
    exec "$@"
fi

# Docker named volumes (and fresh bind mounts) are root-owned by default, which
# blocks the non-root app user from writing SQLite/Drain3 state. Fix ownership
# of any writable data directories mounted under /app/data before dropping
# privileges.
if [ -d /app/data ]; then
    chown -R appuser:appuser /app/data
fi

exec gosu appuser "$@"
