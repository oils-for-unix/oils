#!/usr/bin/env bash
#
# Build steps invoked by Ninja.
#
# Usage:
#   ./build-steps.sh <function name>
#
# TODO: build/actions.sh should be renamed build/build-steps.sh?  "actions"
# implies a side effect, where as "steps" largely know their outputs an outputs
# largely

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
readonly REPO_ROOT

source $REPO_ROOT/mycpp/common.sh
source $REPO_ROOT/test/tsv-lib.sh  # time-tsv
source $REPO_ROOT/build/common.sh  # for CXX, BASE_CXXFLAGS, ASAN_SYMBOLIZER_PATH

readonly ASAN_FLAGS='-O0 -g -fsanitize=address'

asdl-tool() {
  export GC=1  # asdl/tool.py reads this

  PYTHONPATH="$REPO_ROOT:$REPO_ROOT/vendor" $REPO_ROOT/asdl/tool.py "$@"
}

asdl-mypy() {
  local in=$1
  local out=$2
  asdl-tool mypy $in > $out
}

asdl-cpp() {
  local in=$1
  local out_prefix=$2
  asdl-tool cpp $in $out_prefix
}

gen-main() {
  local main_module=${1:-fib_iter}
  cat <<EOF

int main(int argc, char **argv) {
  // gc_heap::gHeap.Init(512);
  gc_heap::gHeap.Init(128 << 10);  // 128 KiB; doubling in size
  // gc_heap::gHeap.Init(400 << 20);  // 400 MiB to avoid garbage collection

  if (getenv("BENCHMARK")) {
    fprintf(stderr, "Benchmarking...\n");
    $main_module::run_benchmarks();
  } else {
    $main_module::run_tests();
  }
}
EOF
}

wrap-cc() {
  local main_module=$1
  local in=$2
  local preamble_path=$3
  local out=$4

  {
     echo "// examples/$main_module"
     echo

     if test -f "$preamble_path"; then
       echo "#include \"$preamble_path\""
     fi

     cat $in

     # main() function
     gen-main $main_module

  } > $out
}

translate() {
  ### Translate Python/MyPy to C++.

  local out=$1
  shift  # rest of args are inputs

  export GC=1  # mycpp_main.py reads this

  # NOTE: mycpp has to be run in the virtualenv, as well as with a different
  # PYTHONPATH.
  ( source $MYCPP_VENV/bin/activate
    # flags may be empty
    time PYTHONPATH=$MYPY_REPO ./mycpp_main.py "$@" > $out
  )
}

compile() {
  ### Compile C++ with various flags

  local variant=$1
  local out=$2
  local more_cxx_flags=$3
  shift 3
  # Now "$@" are the inputs

  #argv COMPILE "$variant" "$out" "$more_cxx_flags"

  local flags="$BASE_CXXFLAGS $more_cxx_flags"

  case $out in
    (*/bin/unit/*)
      flags+=' -I ../cpp'  # for greatest.h
      ;;
  esac

  case $variant in
    (asan)
      flags+=" $ASAN_FLAGS"  # from run.sh
      ;;
    (opt)
      flags+=' -O2 -g'  # -g so you can debug crashes?
      ;;
    (gc_debug)
      # TODO: GC_REPORT and GC_VERBOSE instead?
      flags+=' -g -D GC_PROTECT -D GC_DEBUG -D GC_EVERY_ALLOC'
      ;;
    (*)
      die "Invalid variant: $variant"
      ;;
  esac

  # Note: needed -lstdc++ for 'operator new', which we're no longer using.  But
  # probably exceptions too.

  set -x
  $CXX -o $out $flags -I $REPO_ROOT -I . "$@" -lstdc++
}

strip_() {
  local in=$1
  local out=$2

  # TODO: there could be 2 outputs: symbols + binary
  strip -o $out $in
}

task() {
  local bin=$1  # Run this
  local task_out=$2
  local log_out=$3

  shift 3
  # The rest of the args are passed as flags to time-tsv

  case $bin in
    _ninja/bin/*.asan)
      # We could detect leaks when GC is turned on?
      export ASAN_OPTIONS='detect_leaks=0'
      ;;

    examples/*.py)
      # we import mycpp.mylib and pylib.collections_
      export PYTHONPATH=".:$REPO_ROOT/vendor:$REPO_ROOT"
      ;;
  esac

  case $task_out in
    _ninja/tasks/benchmark/*)
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

# Use repo in the virtualenv
mypy() {
  ( source $MYCPP_VENV/bin/activate
    PYTHONPATH=$MYPY_REPO python3 -m mypy "$@";
  )
}

typecheck() {
  ### Typecheck without translation
  local main_py=$1
  local out=$2

  # Note: MYPYPATH added for examples/parse.py, which uses mycpp.mylib
  #MYPYPATH="$REPO_ROOT:$REPO_ROOT/native" \
  MYPYPATH="$REPO_ROOT:$REPO_ROOT/mycpp" \
    mypy --py2 --strict $main_py > $out
}

lines() {
  for line in "$@"; do
    echo $line
  done
}

checksum() {
  lines "$@" | sort | xargs md5sum
}

# TODO: Could rewrite this in shell:
# - md5sum
# - read hash1 path1; read hash2 path2;
# - and then invoke diff if they're not equal

compare-pairs() {
  python2 -c '
from __future__ import print_function

import subprocess
import sys

def Check(left, right):
  with open(left) as f1, open(right) as f2:
    b1 = f1.read()
    b2 = f2.read()

  if b1 != b2:
    print("%s != %s" % (left, right))
    # Only invoke a subprocess when they are NOT equal
    subprocess.call(["diff", "-u", left, right])
    return False

  return True

num_failures = 0

paths = sys.argv[1:]
n = len(paths)
i = 0
while i < n:
  log_path = paths[i]
  py_path = paths[i+1]

  #print(log_path, py_path)

  if not Check(log_path, py_path):
    num_failures += 1
  else:
    print("OK %s" % log_path)
    print("   %s" % py_path)

  i += 2

if num_failures != 0:
  print("logs-equal: %d failures" % num_failures)
  sys.exit(1)
' "$@"
}

logs-equal() {
  local out=$1
  shift

  {
    compare-pairs "$@"
    # echo
    # checksum "$@" 
  } | tee $out
}

"$@"
