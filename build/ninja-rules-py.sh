#!/usr/bin/env bash
#
# Ninja rules for translating Python to C++.
#
# Usage:
#   build/ninja-rules-py.sh <function name>
#
# Env variables:
#   _bin/shwrap/mycpp_main respects EXTRA_MYCPP_ARGS
#    for --stack-roots-warn 16 in CI

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source build/dev-shell.sh  # python2 in $PATH
#source devtools/types.sh  # typecheck-files
source $REPO_ROOT/test/tsv-lib.sh  # time-tsv

die() {
  echo "$@" >& 2
  exit 1
}

example-main-wrapper() {
  ### Used by mycpp/examples
  local name_namespace=${1:-fib_iter}

  cat <<EOF
int main(int argc, char **argv) {
  gHeap.Init();

  char* b = getenv("BENCHMARK");
  if (b && strlen(b)) {  // match Python's logic
    fprintf(stderr, "Benchmarking...\\n");
    $name_namespace::run_benchmarks();
  } else {
    $name_namespace::run_tests();
  }

  gHeap.CleanProcessExit();
}
EOF
}

main-wrapper() {
  ### Used by oils-for-unix and yaks
  local main_namespace=$1

  cat <<EOF
int main(int argc, char **argv) {
  mylib::InitCppOnly();  // Initializes gHeap

  auto* args = Alloc<List<BigStr*>>();
  for (int i = 0; i < argc; ++i) {
    args->append(StrFromC(argv[i]));
  }

  int status = $main_namespace::main(args);

  gHeap.ProcessExit();

  return status;
}
EOF
}

print-wrap-cc() {
  local out=$1
  local main_func=$2
  local main_namespace=$3
  local in=$4
  local preamble_path=$5

  echo "// $out - generated from Python source code"
  echo

  if test -f "$preamble_path"; then
    echo "#include \"$preamble_path\""
  fi

  cat $in

  # example-main-wrapper, main-wrapper, etc.
  $main_func $main_namespace
}

wrap-cc() {
  local out=$1

  # $translator $main_namespace $in $preamble_path
  print-wrap-cc "$@" > $out
}

# TODO: Move mycpp/example tasks out of Ninja since timing is not a VALUE.  It
# depends on the machine, can be done more than once, etc.

task() {
  local bin=$1  # Run this
  local task_out=$2
  local log_out=$3

  shift 3
  # The rest of the args are passed as flags to time-tsv

  case $bin in
    (mycpp/examples/*.py)
      # we import mycpp.mylib
      export PYTHONPATH="$REPO_ROOT/mycpp:$REPO_ROOT/vendor:$REPO_ROOT"
      ;;
  esac

  case $task_out in
    (_test/tasks/benchmark/*)
      export BENCHMARK=1
      ;;
  esac

  time-tsv -o $task_out --rusage "$@" --field $bin --field $task_out -- \
    $bin >$log_out 2>&1
}

example-task() {
  ### Run a program in the examples/ dir, either in Python or C++

  local name=$1  # e.g. 'fib_iter'
  local impl=$2  # 'Python' or 'C++'

  local bin=$3  # Run this
  local task_out=$4
  local log_out=$5

  task $bin $task_out $log_out --field $name --field $impl
}

benchmark-table() {
  local out=$1
  shift

  # TODO: Use QTT header with types?
  { time-tsv --print-header --rusage \
      --field example_name --field impl \
      --field bin --field task_out 

    # Concatenate task files
    cat "$@" 
  } > $out
}

# Copied from devtools/types.sh

MYPY_FLAGS='--strict --no-strict-optional'
typecheck-files() {
  echo "MYPY $@"

  # TODO: Adjust path for mcypp/examples/modules.py
  time MYPYPATH='.:pyext' python3 -m mypy --py2 --follow-imports=silent $MYPY_FLAGS "$@"
}

typecheck() {
  ### Typecheck without translation
  local main_py=$1
  local out=$2
  local skip_imports=${3:-}

  if test -n "$skip_imports"; then
    local more_flags='--follow-imports=silent'
  else
    local more_flags=''
  fi

  # Similar to devtools/types.sh

  local status=0

  set +o errexit
  typecheck-files $main_py > $out
  status=$?
  set -o errexit

  if test $status != 0; then
    echo "FAIL $main_py"
    cat $out
  fi

  return $status
}

logs-equal() {
  local out=$1
  shift

  mycpp/compare_pairs.py "$@" | tee $out
}

#
# shwrap rules
#

shwrap-py() {
  ### Part of shell template for Python executables

  local main=$1
  echo 'PYTHONPATH=$REPO_ROOT:$REPO_ROOT/vendor exec $REPO_ROOT/'$main' "$@"'
}

shwrap-mycpp() {
  ### Part of shell template for mycpp executable

  cat <<'EOF'
MYPYPATH=$1    # e.g. $REPO_ROOT/mycpp
out=$2
shift 2

# Modifies $PATH; do not combine
. build/dev-shell.sh

tmp=$out.tmp  # avoid creating partial files

# The command we want to run
# EXTRA_MYCPP_ARGS is for --stack-root-warn 16, in Soil CI
set -- python3 mycpp/mycpp_main.py --cc-out $tmp ${EXTRA_MYCPP_ARGS:-} "$@"

# If 'time' is on the system, add timing info.  (It's not present on some
# Debian CI images)
if which time >/dev/null; then
  # 'busybox time' supports -f but not --format.
  set -- \
    time -f 'MYCPP { elapsed: %e, max_RSS: %M }' -- \
    "$@"
fi

MYPYPATH="$MYPYPATH" "$@"
status=$?

mv $tmp $out
exit $status
EOF
}

shwrap-pea() {
  ### Part of shell template for pea executable

  cat <<'EOF'
MYPYPATH=$1    # e.g. $REPO_ROOT/mycpp
out=$2
shift 2

tmp=$out.tmp  # avoid creating partial files

# copied from build/dev-shell.sh

USER_WEDGE_DIR=~/wedge/oils-for-unix.org

MYPY_VERSION=0.780
MYPY_WEDGE=$USER_WEDGE_DIR/pkg/mypy/$MYPY_VERSION

PY3_LIBS_VERSION=2023-03-04
site_packages=lib/python3.10/site-packages
PY3_LIBS_WEDGE=$USER_WEDGE_DIR/pkg/py3-libs/$PY3_LIBS_VERSION/$site_packages

PYTHONPATH="$REPO_ROOT:$MYPY_WEDGE:$PY3_LIBS_WEDGE" MYPYPATH="$MYPYPATH" \
  python3 pea/pea_main.py mycpp "$@" > $tmp
status=$?

mv $tmp $out
exit $status
EOF
}

print-shwrap() {
  local template=$1
  local unused=$2
  shift 2

  cat << 'EOF'
#!/bin/sh
REPO_ROOT=$(cd "$(dirname $0)/../.."; pwd)
. $REPO_ROOT/build/py2.sh
EOF

  case $template in
    py)
      local main=$1  # additional arg
      shift
      shwrap-py $main
      ;;
    mycpp)
      shwrap-mycpp
      ;;
    pea)
      shwrap-pea
      ;;
    *)
      die "Invalid template '$template'"
      ;;
  esac

  echo
  echo '# DEPENDS ON:'
  for dep in "$@"; do
    echo "#   $dep"
  done
}

write-shwrap() {
  ### Create a shell wrapper for a Python tool

  # Key point: if the Python code changes, then the C++ code should be
  # regenerated and re-compiled

  local unused=$1
  local stub_out=$2

  print-shwrap "$@" > $stub_out
  chmod +x $stub_out
}

# sourced by devtools/bin.sh
if test $(basename $0) = 'ninja-rules-py.sh'; then
  "$@"
fi
