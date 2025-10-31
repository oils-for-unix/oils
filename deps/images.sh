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
# (2) Bootstrap Wedges
#
#    $0 build wedge-bootstrap-debian-12  # runs init-deb-cache
#
# (3) Build wedges
#
#     build/deps.sh fetch
#     build/deps.sh boxed-wedges-2025
#
# (4) Rebuild an image
#
#     $0 build soil-debian-12      # runs init-deb-cache and populate the cache
#     $0 build soil-test-image T   # reuse package cache from apt-get
#     $0 smoke soil-test-image     # smoke test
#
# (5) Update live version in 'soil/host-shim.sh live-image-tag'
#
# (6) Push Everything you Built
#
#     # pushes both $LATEST_TAG and latest
#     $0 push-many wedge-bootstrap-debian-12 soil-debian-12 soil-test-image
#
# More
# ----
#
# Images: https://hub.docker.com/u/oilshell
#
#    $0 list-tagged      # Show versions of images
#
#    $0 show-cachemount  # show files in apt cache
#
#    $0 prune            # seems to clear the cache

set -o nounset
set -o pipefail
set -o errexit

source deps/podman.sh

DOCKER=${DOCKER:-docker}

readonly LATEST_TAG='v-2025-10-30-a'  # clobbered with make-bin.sh and zsh upgrade

clean-all() {
  dirs='_build/wedge/tmp _build/wedge/binary _build/deps-source'
  #rm -r -f $dirs
  sudo rm -r -f $dirs
}

list() {
  local which=${1:-all}  # all | soil | prep

  local accept=''
  local reject=''
  case $which in
    all)
      reject='^$'
      ;;
    soil)  # 13 soil images
      reject='^(wedge-bootstrap-.*|soil-debian-.*)'
      ;;
    prep)
      # images to prepare
      # 2025-10: *-debian-10 is Debian Buster from 2019, which was retired in
      # 2024.  You can't do sudo apt-get update
      # https://wiki.debian.org/DebianReleases
      accept='^(wedge-bootstrap-debian-12|soil-debian-12)'
      ;;
  esac

  if test -n "$accept"; then
    for name in deps/Dockerfile.*; do
      local image_id=${name//'deps/Dockerfile.'/}
      if [[ "$image_id" =~ $accept ]]; then
        echo $image_id
      fi
    done
  else
    for name in deps/Dockerfile.*; do
      local image_id=${name//'deps/Dockerfile.'/}
      if [[ "$image_id" =~ $reject ]]; then
        continue
      fi
      echo $image_id
    done
  fi
}

list-tagged() {
  sudo $DOCKER images 'oilshell/*' #:v-*'
}

_latest-one() {
  local name=$1
  $DOCKER images "oilshell/$name" | head -n 3
}

_list-latest() {
  # Should rebuild all these
  # Except I also want to change the Dockerfile to use Debian 12
  list-images | xargs -n 1 -- $0 _latest-one
}

list-latest() {
  sudo $0 _list-latest
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

  # OFF by default.  TODO: use_cache setting should be automatic
  local use_cache=${2:-}

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

build-cached() {
  local name=${1:-soil-dummy}
  build "$name" T
}

build-many() {
  echo 'TODO: use_cache should be automatic - all but 2 images use it'
}

build-all() {
  # Should rebuild all these
  # Except I also want to change the Dockerfile to use Debian 12
  list-images | egrep -v 'test-image|ovm-tarball|benchmarks|wedge-bootstrap|debian-12'
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

push-many() {
  for name in "$@"; do
    push $name
  done
}

smoke-script-1() {
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
  python2 -c "import readline; print(readline)"
  echo

  python3 -c "import ssl; print(ssl)"
  echo

  find /usr/lib | grep -i readline
  echo

  ls /wedge/oils-for-unix.org/pkg/python2/
  ls /wedge/oils-for-unix.org/pkg/python2/2.7.18/lib/python2.7/lib-dynload

  ldd /wedge/oils-for-unix.org/pkg/python2/2.7.18/lib/python2.7/lib-dynload/readline.so
  echo

  exit

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

smoke-script-2() {
  echo '
  cd ~/oil
  . build/dev-shell.sh

  # Bug with python2
  #devtools/types.sh soil-run
  #test/lossless.sh soil-run
  #exit

  #test/spec-version.sh osh-version-text

  echo PATH=$PATH

  #which mksh
  #mksh -c "echo hi from mksh"

  #test/spec.sh smoke
  test/spec.sh zsh-assoc

  which python2
  python2 -V
  echo

  which python3
  python3 -V
  echo

  exit

  # Bug with python2
  test/lossless.sh soil-run

  python3 -m mypy core/util.py
  echo

  # test pyflakes
  test/lint.sh py2-lint core/util.py
  echo

  #pea/TEST.sh parse-all
  #pea/TEST.sh run-tests

  re2c --version
  echo

  # cmark.py
  doctools/cmark.sh demo-ours

  bloaty --help
  echo

  exit

  # hm this shows Python
  uftrace --version

  which uftrace
  uftrace=$(which uftrace)

  ls -l ~/oils.DEPS/wedge/uftrace/0.13/bin/uftrace
  uftrace=~/oils.DEPS/wedge/uftrace/0.13/bin/uftrace

  devtools/R-test.sh soil-run

  exit

  cc -pg -o hello deps/source.medo/uftrace/hello.c

  # libmcount-fast is in the uftrace lib/ dir
  ldd $(which uftrace)
  echo

  set -x
  #head /tmp/cache-bust.txt

  $uftrace record hello
  #uftrace replay hello
  echo

  #find /usr -name "libm*.so"
  '
}

_smoke() {
  ### Smoke test of container
  local name=${1:-soil-dummy}
  local tag=${2:-$LATEST_TAG}
  local docker=${3:-$DOCKER}
  local debug_shell=${4:-}

  #$docker run ${prefix}oilshell/$name:$tag bash -c "$(smoke-script-1)"

  local repo_root=$PWD

  local -a flags argv
  if test -n "$debug_shell"; then
    flags=( -i -t )
    argv=( bash )
  else
    flags=()
    argv=( bash -c "$(smoke-script-2)" )
  fi

  $docker run "${flags[@]}" \
    --mount "type=bind,source=$repo_root,target=/home/uke/oil" \
    oilshell/$name:$tag "${argv[@]}"
}

smoke() {
  sudo $0 _smoke "$@"
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

  # mount 'oil' directory as /app.  TODO: Oils
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

todo-debian-12() {
  # 7 images
  grep soil-common deps/Dockerfile.*
}

todo-purity() {
  # TODO: we should pass --network none in $0 build
  #
  # Hm 7 images need pip download, should reduce them
  #
  # There are other sources of impurity, like:
  # building the R-libs wedge
  # soil-wild - we can't download the testdata, etc.
 
  grep -l install-py3-libs deps/Dockerfile.*
}

todo-tree-shake() {
  # We should invoke OSH to generate parts of the dockerfile?  Or use podman
  # probably?
  #
  # Or maybe it's a default layer in soil-debian-12?

  grep task-five deps/Dockerfile.*
}

todo-relative() {
  grep TODO # _build/wedge/relative, not _build/wedge/binary
}

"$@"

