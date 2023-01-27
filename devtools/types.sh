#!/usr/bin/env bash
#
# Usage:
#   devtools/types.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source devtools/common.sh

typecheck-files() {
  # The --follow-imports=silent option allows adding type annotations
  # in smaller steps without worrying about triggering a bunch of
  # errors from imports.  In the end, we may want to remove it, since
  # everything will be annotated anyway.  (that would require
  # re-adding assert-one-error and its associated cruft, though).

  typecheck --follow-imports=silent $MYPY_FLAGS "$@"
  echo
}

typecheck-oil() {
  # TODO: remove --no-warn-unused-ignores and type: ignore in
  # osh/builtin_comp.py after help_.py import isn't conditional

  cat _build/NINJA/oils_cpp/typecheck.txt \
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
  # No more files for now.  Could do tools/osh2oil.py
  # typecheck-more
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
