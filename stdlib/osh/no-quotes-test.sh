#!/usr/bin/env bash

: ${LIB_OSH=stdlib/osh}

source $LIB_OSH/no-quotes.sh  # module under test

source $LIB_OSH/bash-strict.sh
source $LIB_OSH/two.sh  
source $LIB_OSH/task-five.sh

_demo-stderr() {
  echo zzz "$@" >& 2
  return 99
}

test-nq-run() {
  local status

  nq-run status \
    false
  nq-assert 1 = "$status"
}

test-nq-capture() {
  local status stdout

  nq-capture status stdout \
    echo -n hi
  nq-assert 0 = "$status"
  nq-assert 'hi' = "$stdout"

  nq-capture status stdout \
    echo hi
  nq-assert 0 = "$status"
  # Note that we LOSE the last newline!
  #nq-assert $'hi\n' = "$stdout"

  local stderr
  nq-capture-2 status stderr \
    _demo-stderr yyy

  #echo "stderr: [$stderr]"

  nq-assert 99 = "$status"
  nq-assert 'zzz yyy' = "$stderr"

  nq-capture status stdout \
    _demo-stderr aaa

  #echo "stderr: [$stderr]"

  nq-assert 99 = "$status"
  nq-assert '' = "$stdout"
}

test-nq-redir() {
  local status stdout_file

  nq-redir status stdout_file \
    seq 3
  nq-assert 0 = "$status"
  diff -u $stdout_file - << EOF
1
2
3
EOF

  local stderr_file
  nq-redir-2 status stderr_file \
    log $'hi\nthere'
  nq-assert 0 = "$status"

  # TODO: nq-diff - this can diff files and show LINE number of error

  set +o errexit
  diff -u $stderr_file - << EOF
hi
there
EOF
}

task-five "$@"
