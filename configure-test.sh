#!/bin/sh
#
# Usage:
#   ./configure-test.sh <function name>

# Note: set -e and -u are POSIX; maybe the configure script should run with them
#set -o nounset
#set -o pipefail
#set -o errexit

export _OIL_CONFIGURE_TEST=1  # so we don't run main

. $PWD/configure  # define the functions to be tested

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

test_echo_cpp() {
  local output

  # before calling detect_readline
  output="$(echo_cpp 2>&1)"
  if test "$?" = 0; then
    die 'Expected echo_cpp to fail, but succeeded'
  fi
  if ! test "$output" = "$0 ERROR: called echo_cpp before detecting readline."; then
    die "Unexpected echo_cpp output: $output"
  fi

  # pretend detected_readline was called
  detected_readline=1

  # no readline
  output="$(echo_cpp)"
  if ! test "$?" = 0; then
    die 'Expected echo_cpp to succeed, but failed'
  fi
  if ! test "$(head -1 "$output")" = '/* #undef HAVE_READLINE */'; then
    die "Unexpected echo_cpp output: $output"
  fi

  # have readline
  have_readline=1
  output="$(echo_cpp)"
  if ! test "$?" = 0; then
    die 'Expected echo_cpp to succeed, but failed'
  fi
  if ! test "$(head -1 "$output")" = '#define HAVE_READLINE 1'; then
    die "Unexpected echo_cpp output: $output"
  fi

  # clean-up
  detected_readline=''
  have_readline=''
}

test_echo_vars() {
  local output

  # before calling detect_readline
  output="$(echo_shell_vars 2>&1)"
  if test "$?" = 0; then
    die 'Expected echo_shell_vars to fail, but succeeded'
  fi
  if ! test "$output" = "$0 ERROR: called echo_shell_vars before detecting readline."; then
    die "Unexpected echo_shell_vars output: $output"
  fi

  # pretend detect_readline was called
  detected_readline=1

  # no readline
  output="$(echo_shell_vars)"
  if ! test "$?" = 0; then
    die 'Expected echo_shell_vars to succeed, but failed'
  fi
  if ! test "$output" = 'HAVE_READLINE=
READLINE_DIR=
PREFIX=/usr/local
DATAROOTDIR=
STRIP_FLAGS=--gc-sections'; then
    die "Unexpected echo_shell_vars output: $output"
  fi

  # have readline, no readline_dir
  have_readline=1
  output="$(echo_shell_vars)"
  if ! test "$?" = 0; then
    die 'Expected echo_shell_vars to succeed, but failed'
  fi
  if ! test "$output" = 'HAVE_READLINE=1
READLINE_DIR=
PREFIX=/usr/local
DATAROOTDIR=
STRIP_FLAGS=--gc-sections'; then
    die "Unexpected echo_shell_vars output: $output"
  fi

   # have readline, readline_dir present
  have_readline=1
  readline_dir=/path/to/readline
  output="$(echo_shell_vars)"
  if ! test "$?" = 0; then
    die 'Expected echo_shell_vars to succeed, but failed'
  fi
  if ! test "$output" = 'HAVE_READLINE=1
READLINE_DIR=/path/to/readline
PREFIX=/usr/local
DATAROOTDIR=
STRIP_FLAGS=--gc-sections'; then
    die "Unexpected echo_shell_vars output: $output"
  fi

  # clean-up
  detected_readline=''
  have_readline=''
  readline_dir=''
}

soil_run() {
  # Note: could use run-test-funcs

  for func in \
    test_cc_statements \
    test_parse_flags \
    test_echo_cpp \
    test_echo_vars; do

    echo "    $func"
    $func
    echo '    OK'

  done
}

"$@"
