#!/usr/bin/env bash
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

build() {
  sudo docker build --tag oilshell/toil-dummy --file dummy.Dockerfile .
}

push() {
  sudo docker push oilshell/toil-dummy
}

smoke() {
  sudo docker run oilshell/toil-dummy python2 -c 'print("python2")'
}

"$@"
