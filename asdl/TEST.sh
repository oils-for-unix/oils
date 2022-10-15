#!/usr/bin/env bash
#
# Tests for ASDL.
#
# Usage:
#   asdl/TEST.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source devtools/common.sh        # banner
source test/common.sh      # run-test

# Could we turn on the leak detector for the GC tests?
export ASAN_OPTIONS='detect_leaks=0'

unit() {
  ### Run unit tests

  local compiler=${1:-cxx}
  local variant=${2:-asan}

  # TODO: gcevery

  run-one-test 'asdl/gen_cpp_test' $compiler $variant
  echo

  run-one-test 'asdl/gc_test' $compiler $variant
  echo
}

#
# Python codegen
#

readonly PY_PATH='.:vendor/'  # note: could consolidate with other scripts

# NOTE: We're testing ASDL code generation with --strict because we might want
# Oil to pass under --strict someday.
typed-demo-asdl() {
  # We want to exclude ONLY pylib.collections_, but somehow --exclude
  # '.*collections_\.py' does not do it.  So --follow-imports=silent.  Tried
  # --verbose too
  typecheck --strict --follow-imports=silent \
    _devbuild/gen/typed_demo_asdl.py asdl/examples/typed_demo.py

  PYTHONPATH=$PY_PATH asdl/examples/typed_demo.py "$@"
}

check-arith() {
  # NOTE: There are still some Any types here!  We don't want them for
  # translation.

  MYPYPATH=. PYTHONPATH=$PY_PATH typecheck --strict --follow-imports=silent \
    asdl/examples/typed_arith_parse.py \
    asdl/examples/typed_arith_parse_test.py \
    asdl/examples/tdop.py
}

typed-arith-asdl() {
  check-arith

  export PYTHONPATH=$PY_PATH
  asdl/examples/typed_arith_parse_test.py

  banner 'parse'
  asdl/examples/typed_arith_parse.py parse '40+2'
  echo

  banner 'eval'
  asdl/examples/typed_arith_parse.py eval '40+2+5'
  echo
}

check-types() {
  build/py.sh py-asdl-examples

  banner 'typed-arith-asdl'
  typed-arith-asdl

  banner 'typed-demo-asdl'
  typed-demo-asdl
}

"$@"
