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

typecheck-files-2() {
  local manifest=$1
  local strict_none=${2:-}

  # 150 errors left without those flags.  But it doesn't impede translating to
  # C++ since you have nullptr.  Although List[Optional[int]] may be an issue.
  #local flags=''
  local flags
  if test -n "$strict_none"; then
    flags='--strict'
  else
    flags=$MYPY_FLAGS
  fi

  local log_path=_tmp/err.txt
  set +o errexit
  cat $manifest | xargs -- $0 typecheck --follow-imports=silent $flags >$log_path
  local status=$?
  set -o errexit
  if test $status -eq 0; then
    echo 'OK'
  else
    echo
    cat $log_path
    echo
    echo 'FAIL'
    return 1
  fi
}

soil-run() {
  set -x
  mypy_ --version
  set +x

  # Generate osh_eval dependencies.  Though this is overly aggressive
  ./NINJA-config.sh

  banner 'typecheck Oil'
  typecheck-files-2 _build/NINJA/osh_eval/typecheck.txt

  # Ad hoc list of additional files
  banner 'typecheck More'
  typecheck-more
}


"$@"
