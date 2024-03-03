#!/usr/bin/env bash
#
# Usage:
#   benchmarks/tokens.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# See if tokens blow up by doing creating Id.Lit_Slash

count-tokens() {
  local osh=_bin/cxx-opt/osh
  ninja $osh

  for file in benchmarks/testdata/*; do
    echo $file

    # It prints the number of tokens
    $osh --tool tokens $file >/dev/null
  done
}

"$@"
