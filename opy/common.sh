#!/bin/bash
#
# Usage:
#   ./common.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly THIS_DIR=$(cd $(dirname $0) && pwd)

byterun() {
  $THIS_DIR/byterun/__main__.py "$@"
}
