#!/usr/bin/env bash
#
# Usage:
#   demo/glibc_fnmatch.sh run

set -o nounset
set -o pipefail
set -o errexit

run() {
  local name=glibc_fnmatch
  cc -o _tmp/$name demo/$name.c
  _tmp/$name
}

"$@"
