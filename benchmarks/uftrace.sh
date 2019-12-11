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
  #local cmd=(_bin/osh_parse.opt -c 'echo hi')
  #local cmd=(_bin/osh_parse.opt -n configure)
  #local cmd=(_bin/osh_parse.opt -n benchmarks/testdata/configure)
  local cmd=(_bin/osh_parse.uftrace -n benchmarks/testdata/configure-coreutils)
  uftrace record "${cmd[@]}"
}

by-call() {
  uftrace report -s call
}

"$@"
