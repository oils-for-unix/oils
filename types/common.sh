# types/common.sh

typecheck() {
  # we 'import libc' but the source is native/libc.{c,pyi}
  MYPYPATH=.:native PYTHONPATH=. mypy --py2 "$@"
}

readonly MYPY_FLAGS='--strict --no-implicit-optional --no-strict-optional'
readonly OSH_PARSE_MANIFEST='types/osh-parse-manifest.txt'

# Hack because there's an asdl/pretty.py error that's hard to get rid of.
assert-one-error() {
  local log_path=$1

  # Hack to get rid of summary line that appears in some MyPy versions.
  local num_errors=$(grep -F -v 'Found 1 error in 1 file' $log_path | wc -l)

  # 1 type error allowed for asdl/pretty.py, because our --no-strict-optional
  # conflicts with demo/typed and so forth.
  if [[ $num_errors -eq 1 ]]; then

    # Assert that this is the erorr
    if ! grep -q 'asdl/pretty.py' $log_path; then
      cat $log_path
      echo
      echo FAILED
      return 1
    fi

    echo OK
    return 0
  else
    echo
    cat $log_path
    echo

    echo "Expected 1 error, but got $num_errors"
    return 1
  fi
}
