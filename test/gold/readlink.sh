#!/usr/bin/env bash
#
# Test case for OSH readlink.
#
# Note: there is also a demo to run like this:
#
# $ demo/readlink-demo.sh all
#
# Usage:
#   gold/readlink.sh <function name>

set -o nounset
set -o pipefail
#set -o errexit

test-readlink() {
  readlink -f _tmp/gold-bin/readlink
  echo $?

  readlink -f libc.so
  echo $?

  readlink -f /nonexistent
  echo $?

  readlink -f /nonexistent/foo
  echo $?

  return

  # NOTE: busybox doesn't accept multiple arguments.
  echo 'Multiple arguments with an error in the middle'
  readlink -f _tmp/gold-bin/readlink /nonexistent/foo libc.so
  echo $?
}

# For this readlink gold test, we need a custom test driver.
compare() {
  mkdir -p _tmp/gold-bin
  ln -s -f /bin/busybox _tmp/gold-bin/readlink

  _tmp/gold-bin/readlink --help 2>/dev/null
  if test $? -ne 0; then
    echo "busybox readlink not working"
  fi

  # Use the readlink in busybox.
  PATH="_tmp/gold-bin:$PATH" $0 test-readlink > _tmp/busybox-readlink.txt

  # Use the readlink in OSH.
  PATH="bin/:$PATH" $0 test-readlink > _tmp/osh-readlink.txt

  if diff -u _tmp/{busybox,osh}-readlink.txt; then
    echo PASS
  else
    echo FAIL
    return 1
  fi
}

"$@"
