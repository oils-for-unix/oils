#!/usr/bin/env bash
#
# Manage container images for Toil
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

build() {
  local name=${1:-dummy}

  # Uh BuildKit is not the default on Linux!
  # http://jpetazzo.github.io/2021/11/30/docker-build-container-images-antipatterns/
  #
  # It is more parallel and has colored output.
  sudo DOCKER_BUILDKIT=1 docker build --tag oilshell/toil-$name --file $name.Dockerfile .
}

push() {
  local name=${1:-dummy}
  sudo docker push oilshell/toil-$name
}

smoke() {
  ### Smoke test of container
  local name=${1:-dummy}
  sudo docker run oilshell/toil-$name
  sudo docker run oilshell/toil-$name python2 -c 'print("python2")'
}

cmd() {
  ### Run an arbitrary command
  local name=$1
  shift
  sudo docker run oilshell/toil-$name "$@"
}

mount-test() {
  local name=${1:-dummy}

  # mount Oil directory as /app
  sudo docker run \
    --mount "type=bind,source=$PWD/../,target=/app" \
    oilshell/toil-$name sh -c 'ls -l /app'
}

"$@"
