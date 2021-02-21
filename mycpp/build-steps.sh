#!/usr/bin/env bash
#
# Build steps invoked by Ninja.
#
# Usage:
#   ./steps.sh <function name>
#
# Naming Convention:
#
#   ./configure.py - generates build.ninja (TODO: build_graph.py?)
#   steps.sh - invoked BY ninja.  (build-steps.sh?)
#     problem: changing this file should invalidate certain steps!
#   build.ninja
#   ninja.sh - wrapper for 'clean' and 'all'.  Invokes Ninja.
#     - Don't really need this
#   _ninja/ - tree
#
# TODO: build/actions.sh should be renamed build/steps.sh?  "actions" implies a
# side effect, where as "steps" largely know their outputs an outputs largely

set -o nounset
set -o pipefail
set -o errexit

source common.sh  # sets REPO_ROOT
source $REPO_ROOT/build/common.sh  # for CXX

readonly ASAN_FLAGS='-O0 -g -fsanitize=address'

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

cpp-skeleton() {
  local main_module=${1:-fib_iter}
  shift

  cat <<EOF
// examples/$main_module

EOF

  # the raw module
  cat "$@"

  # main() function
  gen-main $main_module
}

translate() {
  ### Translate Python/MyPy to C++.

  local in=$1
  local out=$2

  local name=$(basename $in .py)
  local raw=_ninja/gen/${name}_raw.cc

  export GC=1  # mycpp_main.py reads this

  # NOTE: mycpp has to be run in the virtualenv, as well as with a different
  # PYTHONPATH.
  ( source _tmp/mycpp-venv/bin/activate
    # flags may be empty
    time PYTHONPATH=$MYPY_REPO ./mycpp_main.py $in > $raw
  )

  cpp-skeleton $name $raw > $out
}

compile() {
  ### Compile C++ with various flags

  local variant=$1
  local out=$2
  shift 2
  # Now "$@" are the inputs

  local flags="$CXXFLAGS"

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
  $CXX -o $out $flags -I . "$@" -lstdc++
}

task() {
  local bin=$1  # Run this
  local task_out=$2
  local log_out=$3

  case $bin in
    _ninja/bin/*.asan)
      # copied from run.sh and build/mycpp.sh
      export ASAN_OPTIONS='detect_leaks=0'
      export ASAN_SYMBOLIZER_PATH="$REPO_ROOT/$CLANG_DIR_RELATIVE/bin/llvm-symbolizer"
      ;;

    examples/*.py)
      # for running most examples
      export PYTHONPATH=".:$REPO_ROOT/vendor"
      ;;
  esac

  case $task_out in
    _ninja/tasks/benchmark/*)
      export BENCHMARK=1
      ;;
  esac

  time-tsv -o $task_out --rusage --field $bin --field $task_out -- \
    $bin >$log_out 2>&1
}

# This is the one installed from PIP
#mypy() { ~/.local/bin/mypy "$@"; }

# Use repo in the virtualenv
mypy() {
  ( source _tmp/mycpp-venv/bin/activate
    PYTHONPATH=$MYPY_REPO python3 -m mypy "$@";
  )
}

typecheck() {
  ### Typecheck without translation
  local in=$1
  local out=$2

  # if test "$(type -t typecheck-$name)" = "function"; then
  #  typecheck-$name > $out
  # else

  mypy --py2 --strict $in > $out
}

lines() {
  for line in "$@"; do
    echo $line
  done
}

checksum() {
  lines "$@" | sort | xargs md5sum
}

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
  print("compare-logs: %d failures" % num_failures)
  sys.exit(1)
' "$@"
}

compare-logs() {
  local out=$1
  shift

  {
    compare-pairs "$@"
    # echo
    # checksum "$@" 
  } | tee $out
}

"$@"
