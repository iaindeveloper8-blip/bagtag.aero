#!/bin/sh
set -e

PUID=${PUID:-9997}
PGID=${PGID:-9997}

if [ -n "$TZ" ]; then
    ln -snf "/usr/share/zoneinfo/$TZ" /etc/localtime
    echo "$TZ" > /etc/timezone
fi

CURRENT_GID=$(id -g app)
CURRENT_UID=$(id -u app)

if [ "$PGID" != "$CURRENT_GID" ]; then
    groupmod -g "$PGID" app
fi

if [ "$PUID" != "$CURRENT_UID" ]; then
    usermod -u "$PUID" app
fi

chown -R app:app /data

exec gosu app "$@"
