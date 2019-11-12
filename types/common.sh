# types/common.sh

typecheck() {
  # we 'import libc' but the source is native/libc.{c,pyi}
  MYPYPATH=.:native PYTHONPATH=. mypy --py2 "$@"
}


readonly MYPY_INI='types/mypy.ini'
readonly MYPY_FLAGS="--config-file=$MYPY_INI"
