#!/usr/bin/env bash
#
# Usage:
#   ./yaml.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

log() {
  echo "$@" >& 2
}

travis() {
  local out='.travis.yml'
  devtools/yaml2json.py .travis.yml.in > $out
  log "Wrote $out"
}

sourcehut() {
  local out='.builds/create-cache.yml'
  devtools/yaml2json.py .builds/create-cache.yml.in > $out
  log "Wrote $out"
}

"$@"
