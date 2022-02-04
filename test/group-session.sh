#!/usr/bin/env bash
#
# Test kernel state: the process group and session leader.
#
# Usage:
#   ./group-session.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

show() {
  # by deafult, it shows processes that use the same terminal
  ps -o pid,ppid,pgid,sid,tname,comm
}

"$@"
