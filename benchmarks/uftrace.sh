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

"$@"
