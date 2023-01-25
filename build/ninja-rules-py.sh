#!/usr/bin/env bash
#
# Ninja rules for translating Python to C++.
#
# Usage:
#   build/ninja-rules-py.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source $REPO_ROOT/mycpp/common.sh  # maybe-our-python3
source $REPO_ROOT/test/tsv-lib.sh  # time-tsv

example-main() {
  local main_module=${1:-fib_iter}

  cat <<EOF
int main(int argc, char **argv) {
  gHeap.Init();

  char* b = getenv("BENCHMARK");
  if (b && strlen(b)) {  // match Python's logic
    fprintf(stderr, "Benchmarking...\\n");
    $main_module::run_benchmarks();
  } else {
    $main_module::run_tests();
  }

  gHeap.CleanProcessExit();
}
EOF
}

oils-cpp-main() {
  local main_namespace=$1

  cat <<EOF
int main(int argc, char **argv) {
  mylib::InitCppOnly();  // Initializes gHeap

  auto* args = Alloc<List<Str*>>();
  for (int i = 0; i < argc; ++i) {
    args->append(StrFromC(argv[i]));
  }

  int status = $main_namespace::main(args);

  gHeap.FastProcessExit();

  return status;
}
EOF
}

gen-oils-cpp() {
  local main_name=$1
  local out_prefix=$2
  shift 2  # rest are inputs

  # Put it in _build/tmp so it's not in the tarball
  local tmp=_build/tmp
  mkdir -p $tmp

  local raw_cc=$tmp/oils_cpp_raw.cc
  local cc_out=${out_prefix}.cc

  local raw_header=$tmp/oils_cpp_raw.h
  local header_out=${out_prefix}.h

  local mypypath="$REPO_ROOT:$REPO_ROOT/pyext"

  _bin/shwrap/mycpp_main $mypypath $raw_cc \
    --header-out $raw_header \
    "$@"
    #--to-header osh.cmd_eval \

  { echo "// $main_name.h: translated from Python by mycpp"
    echo
    echo '#ifndef OILS_CPP_MYCPP_H'
    echo '#define OILS_CPP_MYCPP_H'

    cat $raw_header

    echo '#endif  // OILS_CPP_MYCPP_H'

  } > $header_out

  { cat <<EOF
// $main_name.cc: translated from Python by mycpp

// #include "$header_out"

#include "cpp/preamble.h"
EOF

    cat $raw_cc

    oils-cpp-main $main_name
  } > $cc_out
}

print-wrap-cc() {
  local translator=$1
  local main_module=$2
  local in=$3
  local preamble_path=$4

   echo "// examples/$main_module translated by $translator"
   echo

   if test -f "$preamble_path"; then
     echo "#include \"$preamble_path\""
   fi

   cat $in

   # main() function
   case $translator in
     (mycpp)
       example-main $main_module
       ;;
     (pea)
        echo '#include <stdio.h>'
        echo 'int main() { printf("stub\n"); return 1; }'
       ;;
     (*)
       die "Invalid translator $translator"
       ;;
   esac
}

wrap-cc() {
  local out=$1
  shift

  # $translator $main_module $in $preamble_path
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
    (_bin/cxx-asan/*)
      # We could detect leaks when GC is turned on?
      export ASAN_OPTIONS='detect_leaks=0'
      ;;

    (mycpp/examples/*.py)
      # we import mycpp.mylib and pylib.collections_
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

# For consistency, use the copy of MyPy in our mycpp dependencies
mypy() {
  ( source $MYCPP_VENV/bin/activate
    PYTHONPATH=$MYPY_REPO maybe-our-python3 -m mypy "$@";
  )
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

  # $more_flags can be empty
  MYPYPATH="$REPO_ROOT:$REPO_ROOT/mycpp" \
    mypy --py2 --strict $more_flags $main_py > $out
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

. $REPO_ROOT/mycpp/common-vars.sh  # for $MYCPP_VENV $MYPY_REPO

. $MYCPP_VENV/bin/activate  # so MyPy can import

tmp=$out.tmp  # avoid creating partial files

PYTHONPATH="$REPO_ROOT:$MYPY_REPO" MYPYPATH="$MYPYPATH" \
  ../oil_DEPS/python3 mycpp/mycpp_main.py --cc-out $tmp "$@"
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

PYTHONPATH="$REPO_ROOT:$MYPY_REPO" MYPYPATH="$MYPYPATH" \
  ../oil_DEPS/python3 pea/pea_main.py cpp "$@" > $tmp
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
EOF

  case $template in
    (py)
      local main=$1  # additional arg
      shift
      shwrap-py $main
      ;;
    (mycpp)
      shwrap-mycpp
      ;;
    (pea)
      shwrap-pea
      ;;
    (*)
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
