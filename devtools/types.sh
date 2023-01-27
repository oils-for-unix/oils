#!/usr/bin/env bash
#
# Usage:
#   devtools/types.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source devtools/common.sh

readonly MORE_MANIFEST=devtools/typecheck-more.txt

typecheck-files() {
  # The --follow-imports=silent option allows adding type annotations
  # in smaller steps without worrying about triggering a bunch of
  # errors from imports.  In the end, we may want to remove it, since
  # everything will be annotated anyway.  (that would require
  # re-adding assert-one-error and its associated cruft, though).
  $0 typecheck --follow-imports=silent $MYPY_FLAGS "$@"
}

typecheck-more() {
  egrep -v "$COMMENT_RE" $MORE_MANIFEST | xargs -- $0 typecheck-files
}

typecheck-and-log() {
  local manifest=$1
  local more_flags=${2:-}

  # For manual inspection
  local log_path=_tmp/mypy-errors.txt

  set +o errexit
  cat $manifest | xargs -- $0 typecheck --follow-imports=silent $MYPY_FLAGS $more_flags >$log_path
  local status=$?
  set -o errexit

  if test $status -eq 0; then
    echo 'OK'
  else
    echo
    cat $log_path
    echo
    echo "FAIL (copied to $log_path)"
    return 1
  fi
}

check-all() {
  ### Run this locally

  banner 'typecheck oils_cpp'

  # TODO: remove --no-warn-unused-ignores and type: ignore in
  # osh/builtin_comp.py after help_.py import isn't conditional
  typecheck-and-log _build/NINJA/oils_cpp/typecheck.txt --no-warn-unused-ignores

  # Ad hoc list of additional files
  banner 'typecheck More'
  typecheck-more
}

soil-run() {
  set -x
  mypy_ --version
  set +x

  # Generate oils_cpp dependencies.  Though this is overly aggressive
  ./NINJA-config.sh

  check-all
}

"$@"
