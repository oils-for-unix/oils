#!/usr/bin/env bash
#
# Usage:
#   benchmarks/uftrace.sh <function name>
#
# Examples:
#   benchmarks/uftrace.sh record-osh-eval
#   benchmarks/uftrace.sh replay-alloc
#
# TODO:
#  uftrace dump --chrome       # time-based trace
#  uftrace dump --flame-graph

set -o nounset
set -o pipefail
set -o errexit

download() {
  wget --no-clobber --directory _deps \
    https://github.com/namhyung/uftrace/archive/v0.9.3.tar.gz
}

build() {
  cd _deps/uftrace-0.9.3
  ./configure
  make

  # It can't find some files unless we do this
  echo 'Run sudo make install'
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
record-osh-eval() {
  #local flags=(-F process::Process::RunWait -F process::Process::Process)

  # It's faster to filter just those functino calls
  # record allocation sizes
  # first arg is 'this'
  local flags=( -F MarkSweepHeap::Allocate -A MarkSweepHeap::Allocate@arg2 )

  # Why isn't this showing up?  Is it because of placement new or something?
  #local flags=( -F 'syntax_asdl::Token' )

  uftrace record "${flags[@]}" _bin/cxx-uftrace/osh_eval "$@"

  # Hint: ls -l uftrace.data to make sure this filtering worked!
  ls -l --si uftrace.data/
}

record-execute() {
  record-osh-eval -c 'echo hi > _tmp/redir'
}

record-parse() {
  local path=${1:-benchmarks/testdata/abuild}

  # 635 MB of trace data for this file, Allocate() calls only
  #local path=${1:-benchmarks/testdata/configure-coreutils}

  record-osh-eval --ast-format none -n $path
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
  # These manual filters speed it up
  uftrace script \
    -C 'Dict::Dict' \
    -C 'List::List' \
    -C 'Str::Str' \
    -C 'Tuple2::Tuple2' \
    -C 'Tuple3::Tuple3' \
    -C 'Tuple4::Tuple4' \
    -C 'operator new' \
    -C 'malloc' \
    -S benchmarks/uftrace_plugin.py
}

plugin-allocs() {
  # On the big configure-coreutils script, this takes 10 seconds.  That's
  # acceptable.  Gives 2,402,003 allocations.

  time uftrace script \
    -D 1 \
    -F 'MarkSweepHeap::Allocate' \
    -S benchmarks/uftrace_allocs.py > _tmp/allocs.txt

  # Make allocation size histogram
  sort -n _tmp/allocs.txt | uniq -c | sort -n -r | head -n 20
}

"$@"
