#!/bin/bash
#
# Usage:
#   ./strace-redirects.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

rtrace() {
  ### trace relevant calls
  #strace -e open,fcntl,dup2,close -P _tmp/out.txt -- "$@"
  strace -e open,fcntl,dup2,close -- "$@"
}

invalid() {
  local sh=$1
  local code='true 9> _tmp/out.txt'
  local code='true > _tmp/out.txt'
  #local code='exec 3>_tmp/3.txt; echo hello >&3; exec 3>&-; cat _tmp/3.txt'

  #local code='exec 4>_tmp/4.txt; echo hello >&4; exec 4>&-; cat _tmp/4.txt'
  #local code='true 2>&1'

  sh -c "$code"


  echo
  echo "--- $sh ---"
  echo
  rtrace $sh -c "$code"
}

"$@"
