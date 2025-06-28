#!/usr/bin/env bash
#
# Usage:
#   ./spec-export.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/dev-shell.sh

download-yq() {
  local dir=_tmp/yq
  mkdir -p $dir
  wget --no-clobber --directory "$dir" \
    https://github.com/mikefarah/yq/releases/download/v4.45.4/yq_linux_amd64.tar.gz
}

# this is a Python yq, that doesn't use multi-line strings for readability?
BAD-install-yq() {
  sudo apt-get install yq
}

yq() {
  _tmp/yq/yq_linux_amd64 "$@"
}

yq-demo() {
  #jq -n --slurpfile one <(seq 1 4) --slurpfile five <(seq 5 6) '{one: $one, five: $five}'

  # -P pretty prints
  jq -R -s '{this_script: ., assertions: [1, 2, {shell: "mksh"}]}' < $0 | yq  eval -P
}

# TODO: massage this format more
export-demo() {
  for name in spec/as*.test.sh; do
    test/sh_spec.py --export-json $name | yq eval -P
  done
}

"$@"
