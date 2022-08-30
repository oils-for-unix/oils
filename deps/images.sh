#!/usr/bin/env bash
#
# Manage container images for Soil
#
# Usage:
#   deps/images.sh <function name>
#
# Example: Rebuild an image:
#
#   deps/images.sh build cpp
#   deps/images.sh smoke cpp
#
# Update tag, then
#   deps/images.sh tag cpp
#   deps/images.sh push cpp v-2022-08-29
#
#   Update live version in 'soil/host-shim.sh live-image-tag'
#
# Also useful:
#
#   deps/images.sh list-tagged

set -o nounset
set -o pipefail
set -o errexit

# BUGS in Docker.
#
# https://stackoverflow.com/questions/69173822/docker-build-uses-wrong-dockerfile-content-bug

prune() {
  sudo docker builder prune -f
}

build() {
  local name=${1:-dummy}
  local use_cache=${2:-}  # OFF by default

  local -a flags
  if test -n "$use_cache"; then
    flags=()
  else
    flags=('--no-cache=true')
  fi

  # Uh BuildKit is not the default on Linux!
  # http://jpetazzo.github.io/2021/11/30/docker-build-container-images-antipatterns/
  #
  # It is more parallel and has colored output.

  sudo DOCKER_BUILDKIT=1 \
    docker build "${flags[@]}" --tag oilshell/soil-$name --file deps/Dockerfile.$name .
}

tag() {
  local name=${1:-dummy}

  local tag='v-2022-08-29'
  sudo docker tag oilshell/soil-$name:latest oilshell/soil-$name:$tag 
}

list-images() {
  for name in deps/Dockerfile.*; do
    local image_id=${name//'deps/Dockerfile.'/}
    if test "$image_id" = 'test-image'; then
      continue
    fi
    echo $image_id
  done
}

tag-all() {
  list-images | xargs --verbose -- $0 tag $image
}

list-tagged() {
  sudo docker images 'oilshell/soil-*:v-*'
}

push() {
  local name=${1:-dummy}
  local tag=${2:-}

  local image
  if test -n "$tag"; then
    image="oilshell/soil-$name:$tag"
  else
    image="oilshell/soil-$name:latest"
  fi

  sudo docker push $image
}

smoke() {
  ### Smoke test of container
  local name=${1:-dummy}

  #sudo docker run oilshell/soil-$name
  #sudo docker run oilshell/soil-$name python2 -c 'print("python2")'

  sudo docker run oilshell/soil-$name bash -c '
echo "bash $BASH_VERSION"
for name in python python2 python3; do
  if which $name; then
    $name -V
  else
    echo "$name not found"
  fi
done
'

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

utf8() {
  # needed for a spec test, not the default on Debian
  cmd ovm-tarball bash -c 'LC_ALL=en_US.UTF-8; echo $LC_ALL'
}

mount-test() {
  local name=${1:-dummy}

  local -a argv
  if test $# -le 1; then
    argv=(sh -c 'ls -l /home/uke/oil')
  else
    argv=( "${@:2}" )  # index 2 not 1, weird shell behavior
  fi

  # mount Oil directory as /app
  sudo docker run \
    --mount "type=bind,source=$PWD,target=/home/uke/oil" \
    oilshell/soil-$name "${argv[@]}"
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
