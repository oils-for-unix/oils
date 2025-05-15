#!/usr/bin/env bash
#
# Usage:
#   build/old-ovm-test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

test-oil-bundle() {
  make _bin/oil.ovm
  _bin/oil.ovm osh -c 'echo hi'
  ln -s -f oil.ovm _bin/osh
  _bin/osh -c 'echo hi from osh'
}

# Test the different entry points.
ovm-main-func() {
  echo ---
  echo 'Running nothing'
  echo ---
  local ovm=_build/hello/ovm-dbg

  _OVM_RUN_SELF=0 $ovm || true

  echo ---
  echo 'Running bytecode.zip'
  echo ---

  _OVM_RUN_SELF=0 $ovm _build/hello/bytecode.zip || true

  # Doesn't work because of stdlib deps?
  echo ---
  echo 'Running lib.pyc'
  echo ---

  _OVM_RUN_SELF=0 $ovm build/testdata/lib.pyc

}

"$@"
