#!/bin/bash

OSH_BIN="/usr/local/bin/oils-for-unix"
if [ "$1" = "-c" ] && [ "$2" = "--" ]; then
    shift 2
    exec "$OSH_BIN" osh -c "$@"
else
    exec "$OSH_BIN" osh "$@"
fi
