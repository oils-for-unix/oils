#!/usr/bin/env bash
#
# Build steps invoked by Ninja.
#
# Usage:
#   mycpp/NINJA-steps.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source $REPO_ROOT/mycpp/common.sh  # maybe-our-python3
source $REPO_ROOT/test/tsv-lib.sh  # time-tsv
source $REPO_ROOT/build/common.sh  # for CXX, BASE_CXXFLAGS, ASAN_SYMBOLIZER_PATH

example-main() {
  local main_module=${1:-fib_iter}

  cat <<EOF
int main(int argc, char **argv) {
  // gHeap.Init(512);
  gHeap.Init(128 << 10);  // 128 KiB; doubling in size
  // gHeap.Init(400 << 20);  // 400 MiB to avoid garbage collection

  char* b = getenv("BENCHMARK");
  if (b && strlen(b)) {  // match Python's logic
    fprintf(stderr, "Benchmarking...\\n");
    $main_module::run_benchmarks();
  } else {
    $main_module::run_tests();
  }
}
EOF
}

osh-eval-main() {
  local name=$1

  cat <<EOF
int main(int argc, char **argv) {

  complain_loudly_on_segfault();

  gHeap.Init(400 << 20);  // 400 MiB matches dumb_alloc.cc

  // NOTE(Jesse): Turn off buffered IO
  setvbuf(stdout, 0, _IONBF, 0);
  setvbuf(stderr, 0, _IONBF, 0);

  auto* args = Alloc<List<Str*>>();
  for (int i = 0; i < argc; ++i) {
    args->append(StrFromC(argv[i]));
  }
  int status = 0;

  // For benchmarking
  const char* repeat = getenv("REPEAT");
  if (repeat) {
    Str* r = StrFromC(repeat);
    int n = to_int(r);
    log("Running %d times", n);
    for (int i = 0; i < n; ++i) { 
      status = $name::main(args);
    }
    // TODO: clear memory?
  } else {
    status = $name::main(args);
  }

#ifdef DUMB_ALLOC
  dumb_alloc::Summarize();
#endif
  return status;
}
EOF
}

gen-osh-eval() {
  local out_prefix=$1
  shift  # rest are inputs

  # Put it in _build/tmp so it's not in the tarball
  local tmp=_build/tmp
  mkdir -p $tmp

  local raw=$tmp/osh_eval_raw.cc
  local cc_out=${out_prefix}.cc

  local mypypath="$REPO_ROOT:$REPO_ROOT/pyext"
  _bin/shwrap/mycpp_main $mypypath $raw "$@"

  { 
    local name='osh_eval'
    cat <<EOF
// $name.cc: translated from Python by mycpp

#include "cpp/leaky_preamble.h"  // hard-coded stuff
EOF

    cat $raw

    osh-eval-main $name
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
    cat "$@" 
  } > $out
}

# This is the one installed from PIP
#mypy() { ~/.local/bin/mypy "$@"; }

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

lines() {
  for line in "$@"; do
    echo $line
  done
}

checksum() {
  lines "$@" | sort | xargs md5sum
}

logs-equal() {
  local out=$1
  shift

  mycpp/compare_pairs.py "$@" | tee $out
}

if test $(basename $0) = 'NINJA-steps.sh'; then
  "$@"
fi
