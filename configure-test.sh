#!/bin/sh
#
# Usage:
#   ./configure-test.sh <function name>

# Note: set -e and -u are POSIX; maybe the configure script should run with them
#set -o nounset
#set -o pipefail
#set -o errexit

export _OIL_CONFIGURE_TEST=1  # so we don't run main

. $PWD/configure  # define the functions to be test

test_configure() {
  cc_print_expr 'sizeof(int)'

  local actual
  actual=$(cat $TMP/print_expr.out)
  if ! test "$actual" = 4; then
    die "Expected 4, got $actual"
  fi

  if ! check_sizeof SIZEOF_INT 'int' 4; then
    die "FAILED"
  fi
  # failing test
  #check_sizeof SIZEOF_INT 'int' 8

  if ! cc_statement HAVE_INT 'int x = (int)0;'; then
    die "FAILED"
  fi

  if cc_statement HAVE_FOO 'foo x = (foo)0;'; then
    die "Expected to fail"
  fi
}

soil_run() {
  test_configure
}

"$@"
