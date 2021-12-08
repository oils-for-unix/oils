# types/common.sh

mypy_() {
  local system=mypy
  local pip_global=/usr/local/bin/mypy
  local pip_user=~/.local/bin/mypy

  if test -x $pip_user; then
    $pip_user "$@"
  elif test -x $pip_global; then
    $pip_global "$@"
  else
    $system "$@"
  fi
}

typecheck() {
  # we 'import libc' but the source is native/libc.{c,pyi}

  MYPYPATH=.:native PYTHONPATH=. mypy_ --py2 "$@"
}

readonly MYPY_FLAGS='--strict --no-implicit-optional --no-strict-optional'
readonly OSH_EVAL_MANIFEST='types/osh-eval-manifest.txt'
readonly COMMENT_RE='^[ ]*#'

osh-eval-manifest() {
  egrep -v "$COMMENT_RE" $OSH_EVAL_MANIFEST  # allow comments
}
