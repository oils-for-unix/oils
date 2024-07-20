#!/usr/bin/env bash
#
# Manual setup
#
# Usage:
#   soil/admin.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

keygen() {
  local comment=${1:-oils github}
  local file=${2:-rsa_oils_github}
  ssh-keygen -t rsa -b 4096 -C "$comment" -f $file
}


"$@"
