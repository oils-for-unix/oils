#!/usr/bin/env bash
#
# Usage:
#   ./ninja.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

config() {
  ./configure.py
  cat build.ninja
}

all() {
  ./configure.py
  ninja
}

clean() {
  rm --verbose -r -f _ninja
}

loop() {
  #clean

  set +o errexit
  all
  set -o errexit

  echo

  # Borrowed from benchmark-all
  echo $'status\telapsed_secs\tuser_secs\tsys_secs\tmax_rss_KiB\tbin\ttask_out'
  cat _ninja/tasks/*/*.task.txt
}

"$@"
