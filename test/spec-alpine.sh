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

builtin-bracket() {
  # some tests depend on 'bin' existing
  # Also running as root so you can read anything!  Doh!  Need a real user.
  sh-spec spec/builtin-bracket.test.sh --no-cd-tmp --osh-failures-allowed 3 \
    $SH "$@"
}

# This is bash/OSH only
builtin-completion() {
  # 8 failures instead of 1
  sh-spec spec/builtin-completion.test.sh \
    --no-cd-tmp --osh-failures-allowed 8 \
    $SH "$@"
}

builtin-eval-source() {
  sh-spec spec/builtin-eval-source.test.sh --no-cd-tmp $SH "$@"
}

builtin-trap() {
  sh-spec spec/builtin-trap.test.sh --no-cd-tmp --osh-failures-allowed 3 \
    $SH "$@"
}

builtins() {
  # 6 failures instead of 1
  sh-spec spec/builtins.test.sh --no-cd-tmp --osh-failures-allowed 6 \
    $SH "$@"
}

errexit-oil() {
  sh-spec spec/errexit-oil.test.sh --no-cd-tmp $SH "$@"
}

glob() {
  # 11 failures rather than 7 under Ubuntu.  Probably due to musl libc globbing
  # differences.
  sh-spec spec/glob.test.sh --no-cd-tmp --osh-failures-allowed 11 \
    $SH "$@"
}

introspect() {
  sh-spec spec/introspect.test.sh --no-cd-tmp \
    $SH "$@"
}

loop() {
  # 1 failure instead of 0
  sh-spec spec/loop.test.sh --no-cd-tmp --osh-failures-allowed 1 \
    $SH "$@"
}

smoke() {
  # 1 failure instead of 0
  sh-spec spec/smoke.test.sh --osh-failures-allowed 1 $SH "$@"
}

strict-options() {
  sh-spec spec/strict-options.test.sh --no-cd-tmp $SH "$@"
}

var-op-len() {
  sh-spec spec/var-op-len.test.sh --no-cd-tmp $SH "$@"
}

"$@"
