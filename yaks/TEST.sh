#!/usr/bin/env bash
#
# Usage:
#   yaks/run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/dev-shell.sh  # python3 in PATH
source devtools/run-task.sh
source test/common.sh  # run-test-funcs

build() {
  build/py.sh gen-asdl-py 'yaks/yaks.asdl'
}

check() {
  build

  # Does this do anything?
  local flags='--strict'

  python3 -m mypy $flags yaks/yaks_main.py
}

test-hello() {
  # translate
  yaks/yaks_main.py cpp yaks/examples/hello.yaks

  # type check only
  # yaks/yaks.py check testdata/hello.yaks
}

soil-run() {
  ### Used by soil/worker.sh.  Prints to stdout.

  echo 'DISABLED because ASDL now depends on fastfunc, which is Python 2'
  return

  run-test-funcs

  check
}

run-task "$@"
