# types/common.sh

typecheck() {
  # we 'import libc' but the source is native/libc.{c,pyi}
  MYPYPATH=.:native PYTHONPATH=. mypy --py2 "$@"
}

readonly MYPY_FLAGS='--config-file=types/mypy.ini'
