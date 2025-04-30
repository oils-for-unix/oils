#!/usr/bin/env bash
#
# Manage container images for Soil
#
# Usage:
#   deps/images.sh <function name>
#
# Dirs maybe to clear:
#
#   $0 clean-all  # Start from scratch
#
# Example:
#
# (1) Update LATEST_TAG
#
# (2) Bootstrapping Wedges
#
#    $0 build wedge-bootstrap-debian-12
#
# (3) Building wedges:
#
#    build/deps.sh fetch
#    build/deps.sh boxed-wedges
#    build/deps.sh boxed-spec-bin
#
# (4) Rebuild an image
#
#     $0 build soil-debian-12      # populates apt cache.  WHY DO I NEED THIS?
#     $0 build soil-test-image T   # reuse package cache from apt-get
#     $0 smoke soil-test-image     # smoke test
#
# (5) Update live version in 'soil/host-shim.sh live-image-tag'
#
# (6) Push Everything you Built
#
#     $0 push wedge-bootstrap-debian-12  v-2025-04-30
#     $0 push soil-debian-12  v-2025-04-30
#     $0 push soil-test-image  v-2025-04-30
#
# Our images:
#
#    https://hub.docker.com/u/oilshell
#
#    deps/images.sh list-tagged
#

set -o nounset
set -o pipefail
set -o errexit

source deps/podman.sh

DOCKER=${DOCKER:-docker}

# Build with this tag
readonly LATEST_TAG='v-2025-04-30b'

clean-all() {
  dirs='_build/wedge/tmp _build/wedge/binary _build/deps-source'
  #rm -r -f $dirs
  sudo rm -r -f $dirs
}

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

tag-latest() {
  local name=${1:-wedge-bootstrap-debian-12}
  local tag_built_with=${2:-$LATEST_TAG}

  set -x  # 'docker tag' is annoyingly silent
  sudo $DOCKER tag oilshell/$name:{$tag_built_with,latest}
}

build() {
  local name=${1:-soil-dummy}
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
    --tag "oilshell/$name:$LATEST_TAG" \
    --file deps/Dockerfile.$name .

  # Avoid hassle by also tagging it
  tag-latest $name
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
  list-images | egrep -v 'wedge-builder|bootstrap' | while read image; do
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

  list-images | grep -v 'wedge-builder|bootstrap' | while read image_id; do
    echo "___ $image_id"
    push $image_id latest
  done
}

list-tagged() {
  sudo $DOCKER images 'oilshell/*' #:v-*'
}

push() {
  local name=${1:-soil-dummy}
  local tag=${2:-$LATEST_TAG}

  # TODO: replace with flags
  #export-podman

  local image="oilshell/$name:$tag"

  set -x

  # -E for export-podman vars
  sudo -E $DOCKER push $image
  #sudo -E $DOCKER --log-level=debug push $image

  # Also push the 'latest' tag, to avoid getting out of sync
  sudo -E $DOCKER push oilshell/$name:latest
}

smoke-test-script() {
  echo '
for file in /etc/debian_version /etc/lsb-release; do
  if test -f $file; then
    # spec/ble-idioms tests this
    #grep -E "foo|^10" $file; echo grep=$?

    echo $file
    echo
    cat $file
    echo
  else
    echo "($file does not exist)"
  fi
done

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

#curl https://op.oilshell.org/

if true; then
  python3 -c "import ssl; print(ssl)"
  find /usr/lib | grep -i libssl
  echo

  dpkg -S /usr/lib/x86_64-linux-gnu/libssl.so.3
  echo

  #ls -l /usr/lib/x86_64-linux-gnu/libssl.so.1.1

  apt-cache show libssl-dev

  # find /lib | grep -i libssl
  # echo
  # find /usr/local | grep -i libssl
  # echo
  # python3-config --libs

  # Useful command
  # ldconfig -v #| grep ssl
  # echo

  #find / -name 'libssl.so*'
fi
'
}

smoke() {
  sudo $0 _smoke "$@"
}

_smoke() {
  ### Smoke test of container
  local name=${1:-soil-dummy}
  local tag=${2:-$LATEST_TAG}
  local docker=${3:-$DOCKER}
  local prefix=${4:-}

  #sudo docker run oilshell/$name
  #sudo docker run oilshell/$name python2 -c 'print("python2")'

  # Need to point at registries.conf ?
  #export-podman

  $docker run ${prefix}oilshell/$name:$tag bash -c "$(smoke-test-script)"

  # Python 2.7 build/prepare.sh requires this
  #sudo docker run oilshell/$name python -V

  #sudo docker run oilshell/$name python3 -c 'import pexpect; print(pexpect)'
}

smoke-podman() {
  local name=${1:-dummy}

  # 2025-04: I need to do 'podman login docker.io'
  #
  # Running without root

  # need explicit docker.io prefix with podman
  # smoke $name latest podman docker.io/

  local tag='latest'
  local prefix='docker.io/'
  smoke-test-script | podman run -i ${prefix}oilshell/soil-$name:$tag bash
}

cmd() {
  ### Run an arbitrary command
  local name=${1:-soil-dummy}
  local tag=${2:-$LATEST_TAG}

  shift 2

  sudo $DOCKER run oilshell/$name:$tag "$@"
}

utf8() {
  # needed for a spec test, not the default on Debian
  cmd ovm-tarball bash -c 'LC_ALL=en_US.UTF-8; echo $LC_ALL'
}

mount-test() {
  local name=${1:-soil-dummy}

  local -a argv
  if test $# -le 1; then
    argv=(sh -c 'ls -l /home/uke/oil')
  else
    argv=( "${@:2}" )  # index 2 not 1, weird shell behavior
  fi

  # mount Oil directory as /app
  sudo $DOCKER run \
    --mount "type=bind,source=$PWD,target=/home/uke/oil" \
    oilshell/$name "${argv[@]}"
}

image-history() {
  local image_id=${1:-soil-dummy}
  local tag=${2:-latest}

  local image="oilshell/$image_id"

  sudo $DOCKER history $image:$tag
}

save() {
  local image_id=${1:-soil-dummy}
  local tag=${2:-latest}

  local image="oilshell/$image_id"

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
  local name=${1:-soil-dummy}
  local tag=${2:-$LATEST_TAG}

  local image="oilshell/$name:$tag"

  # Gah this still prints 237M, not the exact number of bytes!
  # --format ' {{ .Size }} ' 
  sudo $DOCKER history --no-trunc $image

  echo $'Size\tVirtual Size'
  sudo $DOCKER inspect $image \
    | jq --raw-output '.[0] | [.Size, .VirtualSize] | @tsv' \
    | commas
}

"$@"
