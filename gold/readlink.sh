#!/bin/bash
#
# Usage:
#   ./readlink.sh <function name>

set -o nounset
set -o pipefail
#set -o errexit

dir-does-not-exist() {
  readlink -f _tmp/gold-bin/readlink
  echo $?

  readlink -f libc.so
  echo $?

  readlink -f /nonexistent
  echo $?

  readlink -f /nonexistent/foo
  echo $?
}

compare() {
  PATH="_tmp/gold-bin:$PATH" $0 dir-does-not-exist > _tmp/busybox-readlink.txt

  PATH="bin/:$PATH" $0 dir-does-not-exist > _tmp/osh-readlink.txt

  diff -u _tmp/busybox-readlink.txt _tmp/osh-readlink.txt
}

"$@"
