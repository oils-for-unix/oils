#!/usr/bin/env bash
#
# Demonstrate compiler features
#
# Usage:
#   build/compiler-demo.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd $(dirname $0)/..; pwd)

source $REPO_ROOT/build/common.sh


# chrome://tracing
# https://aras-p.info/blog/2019/01/16/time-trace-timeline-flame-chart-profiler-for-Clang/
ftime-trace() {
  local dir=_tmp/ftime-trace
  mkdir -p $dir
  rm -f -v $dir/*

  echo ' int foo() { return 32; } ' > $dir/lib.cc
  echo ' int main() { return 42; } ' > $dir/main.cc

  #$CLANGXX --version

  # Compiler annoyances:
  # - -ftime-trace is IGNORED without -c, which means compile without linking
  # - Can't specify -o with multiple source files

  set -x
  $CLANGXX -ftime-trace -o $dir/main.o -c $dir/main.cc 
  $CLANGXX -ftime-trace -o $dir/lib.o -c $dir/lib.cc
  set +x
  echo

  ls -l $dir
  echo

  # .o file is 'relocatable', otherwise it's 'executable'
  file $dir/*
  echo
}

preprocessor() {
  local dir=_tmp/preprocess
  mkdir -p $dir
  rm -f -v $dir/*

  echo '
#include <stdio.h>
int foo() { return 32; }
' > $dir/lib.cc

  # Create a file that gets included twice
  { 
    echo '#ifndef LIB2_H'
    echo '#define LIB2_H'

    # ~13K lines
    echo '#include <vector>' 

    # Almost 32K lines!
    #echo '#include <unordered_map>' 

    # This doesn't make a difference!  The preprocessor strips comments
    for i in $(seq 1000); do
      echo '// comment'
    done

    for i in $(seq 1000); do
      echo "int foo$i() { return $i; }"
    done

    echo '#endif  // LIB2_H'
  } > $dir/lib2.h

  echo '
#include <vector>
#include "lib2.h"  // transitive include

inline int bar() { return 1; }
' > $dir/lib.h

  # wow 12K files for <vector>
  echo '
#include <vector>
#include "lib.h"
#include "lib2.h"  // duplicate include

int main() { return 42; }
' > $dir/main.cc

  $CXX -E $dir/lib.cc > $dir/lib.post.cc

  $CXX -E $dir/main.cc > $dir/main.post.cc

  wc -l $dir/*.post.cc

  # make sure the file compiles
  $CXX -o $dir/main $dir/main.cc
}

duplicate-symbols() {
  local dir=_tmp/duplicate-symbols
  rm -f -v $dir/*
  mkdir -p $dir

  echo '
#ifdef GC
  #include "mycpp/gc_heap.h"
  using gc_heap::Str;
#else
  #include "mycpp/mylib_leaky.h"
#endif

GLOBAL_STR(str0, "hi");

int* g1 = new int[100];

' > $dir/lib.cc

  # Why is it OK to link asdl/runtime.cc and _build/cpp/osh_eval.cc together?
  #
  # Oh they are NOT linked together.  asdl/runtime.cc is only for tests!

  echo '
#ifdef GC
  #include "mycpp/gc_heap.h"
  using gc_heap::Str;
#else
  #include "mycpp/mylib_leaky.h"
#endif

GLOBAL_STR(str0, "hi");

// int* g1 = new int[100];
int* g2 = new int[100];

int main() {
  printf("hi\n");
}
' > $dir/main.cc

  local flags='-D GC'
  $CXX -I . -o $dir/main $flags $dir/lib.cc $dir/main.cc

  $dir/main
}

"$@"
