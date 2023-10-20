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
  build/py.sh gen-asdl-py 'yaks/yaks.asdl' --no-ordered-dict
}

check() {
  build
  # OrderedDict is an issue
  #python3 -m mypy --strict yaks/yaks.py

  # there are some len() errors in asdl/format.py
  local flags='--no-strict-optional'
  #flags=''

  python3 -m mypy $flags yaks/yaks.py
}

test-hello() {
  # translate
  yaks/yaks.py cpp yaks/examples/hello.yaks

  # type check only
  # yaks/yaks.py check testdata/hello.yaks
}

soil-run() {
  ### Used by soil/worker.sh.  Prints to stdout.

  run-test-funcs

  check
}

run-task "$@"
