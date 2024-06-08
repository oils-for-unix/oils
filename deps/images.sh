#!/usr/bin/env bash
#
# Manage container images for Soil
#
# Usage:
#   deps/images.sh <function name>
#
# Example: Rebuild an image:
#
# (1) Update LATEST_TAG
#
# (2) Rebuild
#
#     deps/images.sh build common  # populates apt cache.  WHY DO I NEED THIS?
#     deps/images.sh build cpp T   # reuse package cache from apt-get
#     deps/images.sh smoke cpp
#
# (3) Push image and common
#
#     deps/images.sh push cpp      # pushes the LATEST_TAG
#
#     deps/images.sh list-tagged  # find hash of soil-common
#     sudo docker tag abcdef oilshell/soil-common:latest
#     deps/images.sh push common latest  # update latest, for next Docker build
#
# (4) Update live version in 'soil/host-shim.sh live-image-tag'
#
# Our images:
#
#   https://hub.docker.com/u/oilshell

set -o nounset
set -o pipefail
set -o errexit

source deps/podman.sh

DOCKER=${DOCKER:-docker}

# Build with this tag
readonly LATEST_TAG='v-2024-06-08'

# BUGS in Docker.
#
# https://stackoverflow.com/questions/69173822/docker-build-uses-wrong-dockerfile-content-bug

# NOTE: This also clears the exec.cachemount
prune() {
  sudo $DOCKER builder prune -f
}

# https://stackoverflow.com/questions/62834806/docker-buildkit-cache-location-size-and-id
#
# It lives somewhere in /var/lib/docker/overlay2

show-cachemount() {
  sudo $DOCKER system df -v --format '{{ .BuildCache | json }}' \
    | jq '.[] | select(.CacheType == "exec.cachemount")' | tee _tmp/cachemount.txt

  cat _tmp/cachemount.txt | jq -r '.ID' | while read id; do
    sudo tree /var/lib/docker/overlay2/$id
    sudo du --si -s /var/lib/docker/overlay2/$id
    echo
  done
}

tag-common() {
  local hash=$1  # get hash from $0 list-tagged
  sudo $DOCKER tag $hash oilshell/soil-common:latest
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

  # TODO: use --authfile and more
  #export-podman

  # can't preserve the entire env: https://github.com/containers/buildah/issues/3887
  #sudo --preserve-env=CONTAINERS_REGISTRIES_CONF --preserve-env=REGISTRY_AUTH_FILE \
  sudo -E DOCKER_BUILDKIT=1 \
    $DOCKER build "${flags[@]}" \
    --tag "oilshell/soil-$name:$LATEST_TAG" \
    --file deps/Dockerfile.$name .
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

tag-all-latest() {
  list-images | grep -v 'wedge-builder' | while read image; do
    local tag
    tag=$(soil/host-shim.sh live-image-tag $image)

    echo "$tag $image"

    # syntax: source -> target
    sudo $DOCKER tag oilshell/soil-$image:$tag oilshell/soil-$image:latest
  done
}

push-all-latest() {
  ### 'latest' can lag behind the tagged version, so push to catch up

  # because our 'my-sizes' script fetches the latest manifest

  list-images | grep -v 'wedge-builder' | while read image_id; do
    echo "___ $image_id"
    push $image_id latest
  done
}

list-tagged() {
  sudo $DOCKER images 'oilshell/soil-*:v-*'
}

push() {
  local name=${1:-dummy}
  local tag=${2:-$LATEST_TAG}

  # TODO: replace with flags
  #export-podman

  local image="oilshell/soil-$name:$tag"

  # -E for export-podman vars
  sudo -E $DOCKER push $image
  #sudo -E $DOCKER --log-level=debug push $image
}

smoke() {
  ### Smoke test of container
  local name=${1:-dummy}
  local tag=${2:-$LATEST_TAG}
  local docker=${3:-$DOCKER}
  local prefix=${4:-}

  #sudo docker run oilshell/soil-$name
  #sudo docker run oilshell/soil-$name python2 -c 'print("python2")'

  # Need to point at registries.conf ?
  #export-podman

  sudo $docker run ${prefix}oilshell/soil-$name:$tag bash -c '
echo "bash $BASH_VERSION"

git --version

for name in python python2 python3; do
  if which $name; then
    $name -V
  else
    echo "$name not found"
  fi
done

echo PATH=$PATH
'

  # Python 2.7 build/prepare.sh requires this
  #sudo docker run oilshell/soil-$name python -V

  #sudo docker run oilshell/soil-$name python3 -c 'import pexpect; print(pexpect)'
}

smoke-podman() {
  local name=${1:-dummy}

  # need explicit docker.io prefix with podman
  smoke $name latest podman docker.io/
}

cmd() {
  ### Run an arbitrary command
  local name=${1:-dummy}
  local tag=${2:-$LATEST_TAG}

  shift 2

  sudo $DOCKER run oilshell/soil-$name:$tag "$@"
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
  sudo $DOCKER run \
    --mount "type=bind,source=$PWD,target=/home/uke/oil" \
    oilshell/soil-$name "${argv[@]}"
}

image-history() {
  local image_id=${1:-dummy}
  local tag=${2:-latest}

  local image="oilshell/soil-$image_id"

  sudo $DOCKER history $image:$tag
}

save() {
  local image_id=${1:-dummy}
  local tag=${2:-latest}

  local image="oilshell/soil-$image_id"

  mkdir -p _tmp/images
  local out=_tmp/images/$image_id.tar 

  # Use > instead of -o so it doesn'th have root permissions
  time sudo $DOCKER save $image:$tag > $out
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
  local tag=${2:-$LATEST_TAG}

  local image="oilshell/soil-$name:$tag"

  # Gah this still prints 237M, not the exact number of bytes!
  # --format ' {{ .Size }} ' 
  sudo $DOCKER history --no-trunc $image

  echo $'Size\tVirtual Size'
  sudo $DOCKER inspect $image \
    | jq --raw-output '.[0] | [.Size, .VirtualSize] | @tsv' \
    | commas
}

"$@"
