#!/usr/bin/env bash
#
# Usage:
#   benchmarks/uftrace.sh <function name>
#
# Examples:
#   benchmarks/uftrace.sh record-oils-cpp
#   benchmarks/uftrace.sh replay-alloc
#   benchmarks/uftrace.sh plugin-allocs
#
# TODO:
# - uftrace dump --chrome       # time-based trace
# - uftrace dump --flame-graph  # common stack traces, e.g. for allocation

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh  # R_PATH

download() {
  wget --no-clobber --directory _deps \
    https://github.com/namhyung/uftrace/archive/refs/tags/v0.12.tar.gz
    #https://github.com/namhyung/uftrace/archive/v0.9.3.tar.gz
}

build() {
  cd _deps/uftrace-0.12
  ./configure
  make

  # It can't find some files unless we do this
  echo 'Run sudo make install'
}

ubuntu-hack() {
  # Annoying: the plugin engine tries to look for the wrong file?
  # What's 3.6m.so vs 3.6.so ???

  cd /usr/lib/x86_64-linux-gnu
  ln -s libpython3.6m.so.1.0 libpython3.6.so
}

# https://github.com/namhyung/uftrace/wiki/Tutorial
hello-demo() {
  cat >_tmp/hello.c <<EOF
#include <stdio.h>

int main(void) {
  printf("Hello world\n");
  return 0;
}
EOF

  gcc -o _tmp/hello -pg _tmp/hello.c

  uftrace _tmp/hello
}

# Now we can analyze uftrace.data.
# NOTE: This wasn't that useful because it doesn't give line numbers?

replay() {
  #uftrace replay -F vm::ctx_Redirect::ctx_Redirect

  uftrace replay -F cmd_eval::CommandEvaluator::_Execute
}

# creates uftrace.data/ dir
record-oils-cpp() {
  local out_dir=$1
  local unfiltered=${2:-}
  shift 2

  #local flags=(-F process::Process::RunWait -F process::Process::Process)

  local -a flags

  if test -n "$unfiltered"; then
    out_dir=$out_dir.unfiltered

    # Look for the pattern:
    # Alloc() {
    #   MarkSweepHeap::Allocate(24)
    #   syntax_asdl::line_span::line_span()
    # }
    flags=(
      -F 'Alloc'
      -F 'MarkSweepHeap::Allocate' -A 'MarkSweepHeap::Allocate@arg2'
      -D 2
    )
  else
    # It's faster to filter just these function calls
    flags=(
      -F 'Alloc'  # missing type info
      # arg1 is this, arg2 is num_bytes
      -F 'MarkSweepHeap::Allocate' -A 'MarkSweepHeap::Allocate@arg2'
      # arg 1 is str_len
      -F 'NewStr' -A 'NewStr@arg1'
      -F 'OverAllocatedStr' -A 'OverAllocatedStr@arg1'
      -F 'Str::Str'
      # arg1 is number of elements of type T
      -F 'NewSlab' -A 'NewSlab@arg1'
      -F 'Slab::Slab'
      -F 'NewList' -F 'List::List'
      -F 'List::append'
      -F 'Dict::Dict'  # does not allocate
      -F 'Dict::reserve'  # this allocates
      -F 'Dict::append'
      -F 'Dict::extend'
      -F 'Dict::set'
      -F 'syntax_asdl::Token::Token'
      -D 1
    )

    # Problem: some of these aren't allocations
    # -F 'Tuple2::Tuple2'
    # -F 'Tuple3::Tuple3'
    # -F 'Tuple4::Tuple4'

    # StrFromC calls NewStr, so we don't need it
    # -F 'StrFromC' -A 'StrFromC@arg1' -A 'StrFromC@arg2'
  fi

  local oils_cpp=_bin/cxx-uftrace/oils_cpp 
  ninja $oils_cpp

  time uftrace record -d $out_dir "${flags[@]}" $oils_cpp "$@"
  #time uftrace record $oils_cpp "$@"

  ls -d $out_dir/
  ls -l --si $out_dir/
}

record-parse() {
  local path=${1:-benchmarks/testdata/abuild}

  # For abuild, unfiltered gives 1.6 GB of data, vs. 19 MB filtered!
  local unfiltered=${2:-}

  # 2.3 seconds to parse under -O2, 15 under -O0, which we need
  #local path=${1:-benchmarks/testdata/configure}

  # 9 seconds to parse, 5 seconds to analyze
  #local path=${1:-benchmarks/testdata/configure-coreutils}

  # 635 MB of trace data for this file, Allocate() calls only
  #local path=${1:-benchmarks/testdata/configure-coreutils}

  local out_dir=_tmp/uftrace/parse.data
  mkdir -p $out_dir

  record-oils-cpp $out_dir "$unfiltered" --ast-format none -n $path
}

record-execute() {
  local out_dir=_tmp/uftrace/execute.data
  local unfiltered=${2:-}
  mkdir -p $out_dir

  #local cmd=( benchmarks/compute/fib.sh 10 44 )
  local cmd=( benchmarks/parse-help/pure-excerpt.sh parse_help_file benchmarks/parse-help/mypy.txt )

  record-oils-cpp $out_dir "$unfiltered" "${cmd[@]}"
}

by-call() {
  uftrace report -s call
}

# Results: Tuple, List / Str are more common any individual ASDL types.
#
# Most common:
# word_t / word_part_t base constructor, which does nothing
# syntax_asdl::{Token,line_span}
# And then compound_word is fairly far down.

# NOTE: requires uftrace -00
important-types() {
  local pat='Str::Str|List::List|Tuple.::Tuple|syntax_asdl::'

  # syntax_asdl ... ::tag_() is very common, but we don't care here
  # don't track sum types constructors like word_t::word_t because they're
  # empty
  uftrace report -s call | egrep "$pat" | egrep -v '::tag_|_t::'
}

# Hm this shows EVERY call stack that produces a list!

# uftrace graph usage shown here
# https://github.com/namhyung/uftrace/wiki/Tutorial

# Hot list creation:
# - _ScanSimpleCommand
# - _MakeSimpleCommand
#   - _BraceDetect
#   - _TildeDetect
# - _ReadCompoundWord which instantiates compound_word
# - _MaybeExpandAliases
#
# could you insert manual deletion here?
# or reuse members?  

# TODO: It would actually be better to get the DIRECT ancestor only, not the
# full strack trace.

list-creation() {
  #uftrace graph -f total,self,call 'List::List'
  # This shows how often List::List is called from each site
  uftrace graph -C 'List::List'
}

# Not many dicts!
dict-creation() {
  uftrace graph -C 'Dict::Dict'
}

str-creation() {
  uftrace graph -C 'Str::Str'
}

replay-alloc() {
  # call graph
  #uftrace graph -C 'MarkSweepHeap::Allocate'

  # shows what calls this function
  #uftrace replay -C 'MarkSweepHeap::Allocate'

  # shows what this function calls
  #uftrace replay -F 'MarkSweepHeap::Allocate'

  # filters may happen at record or replay time

  # depth of 1
  #uftrace replay -D 1 -F 'MarkSweepHeap::Allocate'

  uftrace replay -D 1 -F 'MarkSweepHeap::Allocate'
}

plugin() {
  # Note this one likes UNFILTERED data
  uftrace script -S benchmarks/uftrace_plugin.py
}

plugin-allocs() {
  local name=${1:-parse}

  local dir=_tmp/uftrace/$name.data

  # On the big configure-coreutils script, this takes 10 seconds.  That's
  # acceptable.  Gives 2,402,003 allocations.

  local out_dir=_tmp/uftrace/${name}_tsv
  mkdir -p $out_dir
  time uftrace script -d $dir -S benchmarks/uftrace_allocs.py $out_dir

  wc -l $out_dir/*.tsv
}

report() {
  local name=${1:-parse}

  local in_dir=_tmp/uftrace/${name}_tsv

  R_LIBS_USER=$R_PATH benchmarks/report.R alloc $in_dir _tmp/uftrace

  #ls $dir/*.tsv
}

# TODO:
#
# - all heap allocations vs. all string allocations (include StrFromC())
#   - obj length vs. string length
#   - the -D 1 arg interfers?
# - parse workload vs evaluation workload (benchmarks/compute/*.sh)

"$@"
