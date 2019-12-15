#!/bin/bash
#
# Usage:
#   ./uftrace.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

#uftrace() {
#  ~/src/uftrace-0.8.1/uftrace "$@"
#}

download() {
  wget --directory _deps \
    https://github.com/namhyung/uftrace/archive/v0.9.3.tar.gz
}

python-demo() {
  uftrace _devbuild/cpython-instrumented/python -h
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

# Creates uftrace.data
ovm-dbg() {
  make clean 
  make CFLAGS='-O0 -pg' _bin/oil.ovm-dbg
  OVM_VERBOSE=1 uftrace record _bin/oil.ovm-dbg osh "$@"
}

# Now we can analyze uftrace.data.
# NOTE: This wasn't that useful because it doesn't give line numbers?

replay() {
  # Just strace from this module.
  uftrace replay -F FindModule
}

# creates uftrace.data dir
osh-parse() {
  local path=${1:-benchmarks/testdata/configure-coreutils}
  local cmd=(_bin/osh_parse.uftrace -n $path)

  #local cmd=(_bin/osh_parse.opt -c 'echo hi')

  uftrace record "${cmd[@]}"
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

str-creation() {
  #uftrace graph -f total,self,call 'List::List'
  # This shows how often List::List is called from each site
  uftrace graph -C 'Str::Str'
}

plugin() {
  # These manual filters speed it up
  uftrace script \
    -C 'List::List' \
    -C 'Str::Str' \
    -C 'Tuple2::Tuple2' \
    -C 'Tuple3::Tuple3' \
    -C 'Tuple4::Tuple4' \
    -C 'operator new' \
    -C 'malloc' \
    -S benchmarks/uftrace_plugin.py
}

"$@"
