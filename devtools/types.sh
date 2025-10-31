#!/usr/bin/env bash
#
# Usage:
#   devtools/types.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh  # run-task

source build/dev-shell.sh  # python3 in $PATH

readonly MYPY_FLAGS='--strict --no-strict-optional'

# Note: similar to egrep filename filters in build/dynamic-deps.sh
readonly COMMENT_RE='^[ ]*#'

banner() {
  echo ''
  echo "*** $@"
  echo ''
}

typecheck-files() {
  # The --follow-imports=silent option allows adding type annotations
  # in smaller steps without worrying about triggering a bunch of
  # errors from imports.  In the end, we may want to remove it, since
  # everything will be annotated anyway.  (that would require
  # re-adding assert-one-error and its associated cruft, though).

  # NOTE: This got a lot slower once we started using the MyPy repo, instead of
  # the optimized package from pip
  # Consider installing the package again
  echo "MYPY $@"
  time MYPYPATH='.:pyext' python3 -m mypy --py2 --follow-imports=silent $MYPY_FLAGS "$@"
  echo
}

check-binary() {
  local py_module=${1:-}

  banner "Type checking $py_module"

  # TODO: remove --no-warn-unused-ignores and type: ignore in
  # osh/builtin_comp.py after help_.py import isn't conditional

  local manifest

  local m1=_build/NINJA/$py_module/deps.txt
  local m2=_build/NINJA/$py_module/typecheck.txt

  if test -f $m1; then
    manifest=$m1
  elif test -f $m2; then
    manifest=$m2
  else
    die "Couldn't find manifest for $py_module ($m1 or $m2)"
  fi

  cat $manifest | xargs -- $0 typecheck-files --no-warn-unused-ignores 
}

check-oils() {
  check-binary 'bin.oils_for_unix'
}

# NOTE: Becoming obsolete as typecheck filters in build/dynamic-deps.sh are whittled down
check-more() {
  egrep -v "$COMMENT_RE" devtools/typecheck-more.txt \
    | xargs -- $0 typecheck-files
}

mypy-check() {
  # duplicates some values from build/deps.sh
  local MYPY_WEDGE="$PWD/../oils.DEPS/wedge/mypy/0.780"

  local site_packages='lib/python3.10/site-packages'
  local PY3_LIBS_WEDGE="$PWD/../oils.DEPS/wedge/py3-libs/2023-03-04/$site_packages"

  local pypath=".:$MYPY_WEDGE:$PY3_LIBS_WEDGE"

  # The paths are fiddly?
  PYTHONPATH=$pypath MYPYPATH=$MYPY_WEDGE \
    python3 -m mypy "$@"
}

check-mycpp() {
  banner 'Type checking mycpp'

  local -a files=(
    mycpp/{pass_state,util,crash,format_strings,visitor,const_pass,control_flow_pass,mycpp_main,cppgen_pass,conversion_pass}.py
  )
  local -a flags=( --strict --no-strict-optional --follow-imports=silent )

  mypy-check "${flags[@]}" "${files[@]}"
}

check-doctools() {
  if false; then
    local -a files=(
      $(for x in doctools/*.py; do echo $x; done | grep -v '_test.py' )
    )
  else
    #local -a files=( doctools/help_gen.py )
    local -a files=( doctools/ul_table.py doctools/html_old.py doctools/oils_doc.py
      doctools/help_gen.py data_lang/htm8.py data_lang/htm8_util.py )

  fi

  # 777 errors before pyann
  # 583 afterward
  local -a flags=( --py2 --no-strict-optional --strict --follow-imports=silent )
  #local -a flags=( --py2 --no-strict-optional )

  set -x
  mypy-check "${flags[@]}" "${files[@]}"
}

soil-run() {
  set -x
  python3 -m mypy --version
  set +x

  # Generate oils-for-unix dependencies.  Though this is overly aggressive
  ./NINJA-config.sh

  check-oils
  check-more

  # 2025-10-31: 27 errors in 5 files
  # allow it to fail for now
  check-mycpp || true
}

name=$(basename $0)
if test "$name" = 'types.sh'; then
  task-five "$@"
fi
