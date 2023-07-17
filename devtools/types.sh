#!/usr/bin/env bash
#
# Usage:
#   devtools/types.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/dev-shell.sh  # python3 in $PATH
source devtools/run-task.sh  # run-task

readonly MYPY_FLAGS='--strict --no-strict-optional'

# Note: similar to egrep filename filters in build/dynamic-deps.sh
readonly COMMENT_RE='^[ ]*#'

typecheck-files() {
  # The --follow-imports=silent option allows adding type annotations
  # in smaller steps without worrying about triggering a bunch of
  # errors from imports.  In the end, we may want to remove it, since
  # everything will be annotated anyway.  (that would require
  # re-adding assert-one-error and its associated cruft, though).

  # NOTE: This got a lot slower once we started using the MyPy repo, instead of
  # the optimized package from pip
  # Consider installing the package again
  echo "MYPY $@"
  time MYPYPATH='.:pyext' python3 -m mypy --py2 --follow-imports=silent $MYPY_FLAGS "$@"
  echo
}

typecheck-oil() {
  # TODO: remove --no-warn-unused-ignores and type: ignore in
  # osh/builtin_comp.py after help_.py import isn't conditional

  cat _build/NINJA/bin.oils_for_unix/typecheck.txt \
    | xargs -- $0 typecheck-files --no-warn-unused-ignores 
}

# NOTE: Becoming obsolete as typecheck filters in build/dynamic-deps.sh are whittled down
typecheck-more() {
  egrep -v "$COMMENT_RE" devtools/typecheck-more.txt \
    | xargs -- $0 typecheck-files
}

check-all() {
  ### Run this locally

  typecheck-oil 

  # Ad hoc list of additional files
  typecheck-more
}

soil-run() {
  set -x
  python3 -m mypy --version
  set +x

  # Generate oils-for-unix dependencies.  Though this is overly aggressive
  ./NINJA-config.sh

  check-all
}

run-task "$@"
