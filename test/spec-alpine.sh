#!/bin/bash
#
# Analogous to test/spec.sh, but for the environment set up by test/alpine2.sh.
#
# Usage:
#   test/spec-alpine.sh <function name>

set -o nounset
set -o pipefail
set -o errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

source test/common.sh
source test/spec-common.sh

readonly SH=osh  # just use the one in the $PATH

smoke() {
  sh-spec spec/smoke.test.sh $SH "$@"
}

"$@"
