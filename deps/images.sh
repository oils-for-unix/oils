#!/usr/bin/env bash
#
# Manage container images for Soil
#
# Usage:
#   deps/images.sh <function name>
#
# Example: Rebuild an image:
#
#   deps/images.sh build common  # populates apt cache.  WHY DO I NEED THIS?
#   deps/images.sh build cpp T   # reuse package cache from apt-get
#   deps/images.sh smoke cpp
#
# Update tag, then
#   deps/images.sh tag cpp
#   deps/images.sh push cpp
#   deps/images.sh push cpp v-2022-08-29
#   (I don't see why I have to push 'latest' and 'tagged' ?)
#
# Update live version in 'soil/host-shim.sh live-image-tag'
#
# Also useful:
#
#   deps/images.sh list-tagged
#
# URL
#
#   https://hub.docker.com/u/oilshell

set -o nounset
set -o pipefail
set -o errexit

# BUGS in Docker.
#
# https://stackoverflow.com/questions/69173822/docker-build-uses-wrong-dockerfile-content-bug

# NOTE: This also clears the exec.cachemount
prune() {
  sudo docker builder prune -f
}

# https://stackoverflow.com/questions/62834806/docker-buildkit-cache-location-size-and-id
#
# It lives somewhere in /var/lib/docker/overlay2

show-cachemount() {
  sudo docker system df -v --format '{{ .BuildCache | json }}' \
    | jq '.[] | select(.CacheType == "exec.cachemount")' | tee _tmp/cachemount.txt

  cat _tmp/cachemount.txt | jq -r '.ID' | while read id; do
    sudo tree /var/lib/docker/overlay2/$id
    sudo du --si -s /var/lib/docker/overlay2/$id
    echo
  done
}

build() {
  local name=${1:-dummy}
  local use_cache=${2:-}  # OFF by default

  # set -x
  local -a flags
  if test -n "$use_cache"; then
    flags=()
  else
    flags=('--no-cache=true')
  fi
  #flags+=('--progress=plain')

  # Uh BuildKit is not the default on Linux!
  # http://jpetazzo.github.io/2021/11/30/docker-build-container-images-antipatterns/
  #
  # It is more parallel and has colored output.

  sudo DOCKER_BUILDKIT=1 \
    docker build "${flags[@]}" --tag oilshell/soil-$name --file deps/Dockerfile.$name .
}

tag() {
  local name=${1:-dummy}

  local tag='v-2023-02-28'
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

push-all-latest() {
  ### 'latest' can lag behind the tagged version, so push to catch up

  # because our 'my-sizes' script fetches the latest manifest

  list-images | while read image_id; do
    echo "___ $image_id"
    push $image_id
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

git --version

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

image-history() {
  local image_id=${1:-dummy}
  local tag=${2:-latest}

  local image="oilshell/soil-$image_id"

  sudo docker history $image:$tag
}

save() {
  local image_id=${1:-dummy}
  local tag=${2:-latest}

  local image="oilshell/soil-$image_id"

  mkdir -p _tmp/images
  local out=_tmp/images/$image_id.tar 

  # Use > instead of -o so it doesn'th have root permissions
  time sudo docker save $image:$tag > $out
  ls -l -h $out
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
