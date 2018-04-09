#!/bin/bash
#
# Usage:
#   ./opy.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly THIS_DIR=$(cd $(dirname $0) && pwd)

osh-byterun() {
  opy/_tmp/repo-with-opy/bin/osh-byterun "$@"
}

# Show the difference between OSH running under CPython and OSH running under
# byterun.
osh-byterun-speed() {
  pushd $THIS_DIR/..

  local prog='for i in $(seq 10); do echo $i; done'
  time bin/osh -c "$prog"
  time osh-byterun -c "$prog"

  popd
}

osh-byterun-parse() {
  local prog='echo "hello world"'

  pushd $THIS_DIR/..
  time bin/osh -n -c "$prog"
  time osh-byterun -n -c "$prog"
  popd
}

"$@"
