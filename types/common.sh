# types/common.sh

typecheck() {
  # we 'import libc' but the source is native/libc.{c,pyi}
  MYPYPATH=.:native PYTHONPATH=. mypy --py2 "$@"
}

readonly MYPY_FLAGS='--config-file=types/mypy.ini'


# Hack because there's an asdl/pretty.py error that's hard to get rid of.
assert-one-error() {
  local log_path=$1
  echo
  cat $log_path
  echo

  # Hack to get rid of summary line that appears in some MyPy versions.
  local num_errors=$(grep -F -v 'Found 1 error in 1 file' $log_path | wc -l)

  # 1 type error allowed for asdl/pretty.py, because our --no-strict-optional
  # conflicts with demo/typed and so forth.
  if [[ $num_errors -eq 1 ]]; then
    echo OK
    return 0
  else
    echo "Expected 1 error, but got $num_errors"
    return 1
  fi
}
