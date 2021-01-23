# types/common.sh

mypy_() {
  ### Version of mypy that PIP installs

  # This exists too?
  # ~/.local/bin/mypy "$@"
  /usr/local/bin/mypy "$@"
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
