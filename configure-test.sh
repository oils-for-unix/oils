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

test_cc_statements() {
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

test_parse_flags() {
  parse_flags --prefix /usr --datarootdir /usr/local/share

  if ! test "$FLAG_prefix" = '/usr'; then
    die "FAILED - prefix is $FLAG_prefix not /usr"
  fi

  if ! test "$FLAG_datarootdir" = '/usr/local/share'; then
    die "FAILED - datarootdir is $FLAG_datarootdir not /usr/local/share"
  fi

  FLAG_prefix='/usr/local'
  FLAG_datarootdir=''

  parse_flags --prefix /usr

  if ! test "$FLAG_datarootdir" = '/usr/share'; then
    die "FAILED - datarootdir is $FLAG_datarootdir not /usr/share"
  fi

  FLAG_prefix='/usr/local'
  FLAG_datarootdir=''
}

test_detect_cpp() {
  local output

  FLAG_without_readline=1
  output="$(detect_cpp)"

  if ! test "$?" = 0; then
    die "Expected detect_cpp to succeed, but failed"
  fi
  if ! test "$output" = "#define HAVE_READLINE 0"; then
    die "Unexpected detect_cpp output: $output"
  fi

  # test with_readline and unfindable readline
  FLAG_without_readline=''
  FLAG_with_readline=1
  FLAG_readline=/path/to/fake/readline

  output="$(detect_cpp 2>&1)"

  if test "$?" = 0; then
    die "Expected detect_cpp to fail, but succeeded"
  fi
  if ! test "$output" = "$0 ERROR: readline was not detected on the system (--with-readline passed)."; then
    die "Unexpected detect_cpp output: $output"
  fi

  # test neither with_readline nor without_readline and unfindable readline
  FLAG_without_readline=''
  FLAG_with_readline=''
  FLAG_readline=/path/to/fake/readline

  detect_cpp >$TMP/detect_cpp.out

  if ! test "$?" = 0; then
    die "Expected detect_cpp to succeed, but failed"
  fi

  output="$(cat $TMP/detect_cpp.out)"

  if ! test "$output" = "#define HAVE_READLINE 0"; then
    die "Unexpected detect_cpp output: $output"
  fi
  if ! test "$FLAG_without_readline" = 1; then
    die "detect_cpp failed to set FLAG_without_readline"
  fi

  FLAG_with_readline=''
  FLAG_readline=''
}

soil_run() {
  test_cc_statements
  test_parse_flags
  test_detect_cpp
}

"$@"
