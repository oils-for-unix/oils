#!/usr/bin/env bash
#
# Run tests in this directory.
#
# Requires node.js to be installed locally.
#
# Usage:
#   web/TEST.sh search

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

search() {
  node web/search.test.js
}

task-five "$@"
