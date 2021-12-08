# types/common.sh

mypy_() {
  ### Version of mypy that PIP installs

  # Try 3 locations:
  # - system prefix
  # - global pip install prefix
  # - user pip install prefix
  #
  # Which of these search paths should take precedence is an open
  # question.
  #
  # XXX: Is there a shell idiom for parsing a colon-separated path
  # list?
  local system=/usr/bin/mypy
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
