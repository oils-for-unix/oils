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

github-actions() {
  ### Validate and print to stdout
  devtools/yaml2json.py .github/workflows/all-builds.yml
}

bug() {
  # This is wrong: should be 100, not "1e2"

  devtools/yaml2json.py <<EOF
{"foo": 1e2}
EOF

  # Uh this is also wrong
  devtools/yaml2json.py <<EOF
%YAML 1.2
---
{"foo": 1e2}
EOF
}

"$@"
