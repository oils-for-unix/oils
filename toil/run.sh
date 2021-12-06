#!/usr/bin/env bash
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

build() {
  # Uh this is not the default on Linux!
  # http://jpetazzo.github.io/2021/11/30/docker-build-container-images-antipatterns/
  #
  # It is more parallel and has colored output.
  sudo DOCKER_BUILDKIT=1 docker build --tag oilshell/toil-dummy --file dummy.Dockerfile .
}

push() {
  sudo docker push oilshell/toil-dummy
}

smoke() {
  sudo docker run oilshell/toil-dummy
  sudo docker run oilshell/toil-dummy python2 -c 'print("python2")'
}

mount-test() {
  # mount Oil directory as /app
  sudo docker run \
    --mount "type=bind,source=$PWD/../,target=/app" \
    oilshell/toil-dummy sh -c 'ls -l /app'
}

"$@"
