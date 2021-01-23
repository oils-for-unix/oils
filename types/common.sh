# types/common.sh

mypy_() {
  ### Version of mypy that PIP installs

  # Try 2 locations.  There's a weird difference between pip3 install location
  # on Debian vs. Ubuntu
  local first=/usr/local/bin/mypy
  local second=~/.local/bin/mypy

  if test -x $first; then
    $first "$@"
  else
    $second "$@"
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
