#!/usr/bin/env bash
#
# Manage container images for Toil
#
# Usage:
#   soil/images.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

build() {
  local name=${1:-dummy}

  # Uh BuildKit is not the default on Linux!
  # http://jpetazzo.github.io/2021/11/30/docker-build-container-images-antipatterns/
  #
  # It is more parallel and has colored output.
  sudo DOCKER_BUILDKIT=1 \
    docker build --tag oilshell/soil-$name --file soil/$name.Dockerfile .
}

push() {
  local name=${1:-dummy}
  sudo docker push oilshell/soil-$name
}

smoke() {
  ### Smoke test of container
  local name=${1:-dummy}

  #sudo docker run oilshell/soil-$name
  sudo docker run oilshell/soil-$name python2 -c 'print("python2")'

  # Python 2.7 build/prepare.sh requires this
  #sudo docker run oilshell/soil-$name python -V

  #sudo docker run oilshell/soil-$name python3 -c 'import pexpect; print(pexpect)'
}

cmd() {
  ### Run an arbitrary command
  local name=$1
  shift
  sudo docker run oilshell/soil-$name "$@"
}

mount-test() {
  local name=${1:-dummy}

  # mount Oil directory as /app
  sudo docker run \
    --mount "type=bind,source=$PWD/../,target=/app" \
    oilshell/soil-$name sh -c 'ls -l /app'
}

# This shows CREATED, command CREATED BY, size
# It's a human readable size though
#
# This doesn't really have anything better
# https://gist.github.com/MichaelSimons/fb588539dcefd9b5fdf45ba04c302db6
#
# It's annoying that the remote registry API is different than the local API.

layers() {
  local name=${1:-dummy}

  # Gah this still prints 237M, not the exact number of bytes!
  # --format ' {{ .Size }} ' 
  sudo docker history --no-trunc oilshell/soil-$name

  echo $'Size\tVirtual Size'
  sudo docker inspect oilshell/soil-$name \
    | jq --raw-output '.[0] | [.Size, .VirtualSize] | @tsv' \
    | commas
}

"$@"
