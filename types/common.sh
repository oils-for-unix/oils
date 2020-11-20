# types/common.sh

typecheck() {
  # we 'import libc' but the source is native/libc.{c,pyi}
  # note: pip puts mypy in ~/.local/bin.  I also had a confusing
  # /usr/local/bin/mypy.
  MYPYPATH=.:native PYTHONPATH=. ~/.local/bin/mypy --py2 "$@"
}

readonly MYPY_FLAGS='--strict --no-implicit-optional --no-strict-optional'
readonly OSH_EVAL_MANIFEST='types/osh-eval-manifest.txt'
readonly COMMENT_RE='^[ ]*#'

osh-eval-manifest() {
  egrep -v "$COMMENT_RE" $OSH_EVAL_MANIFEST  # allow comments
}
