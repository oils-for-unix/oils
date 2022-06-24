#!/usr/bin/env bash
#
# Usage:
#   ./release-patch.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

version-0.10.0() {
  cp -v \
    _release/VERSION/doc/{idioms,error-handling,oil-language-tour}.html \
    ../oilshell.org__deploy/release/0.10.0/doc/

  cp -v \
    _release/VERSION/web/*.css \
    ../oilshell.org__deploy/release/0.10.0/web/
}

version-0.11.0() {
  cp -v \
    _release/VERSION/doc/{idioms,upgrade-breakage}.html \
    ../oilshell.org__deploy/release/0.11.0/doc/
}

"$@"
