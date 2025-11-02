#!/usr/bin/env bash
#
# Rebuild all OCI containers from scratch
#
# Usage:
#   deps/full-rebuild.sh <function name>
#
# Examples:
#   deps/full-rebuild.sh soil-all  # build boxed wedges; build and push OCI images

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh


# TODO
# 1. wedge-bootstrap: rename uke0 -> uke
#    - hopefully this fixes the uftrace wedge
# 2. make deps/wedge.sh boxed builds work with rootless podman
#    - right now deps/images.sh can run rootless
# 3. migrate to --network none
#    - for wedge builds
#    - for image builds
#      - not sure how it interacts with apt
# 4. everything with raw crun - requires some other rewrites
# 5. coarse tree-shaking for task-five.sh, etc.

# MORE WEDGES
# - uftrace, as mentioned above
# - test/wild.sh - oil_DEPS ->
# - ovm-tarball - oil_DEPS -> ../oils.DEPS/wedge/python2-slice
# - clang binary - contributors use this
# - benchmarks/osh-runtime files
# - py3-libs wedge - it has dependencies
#   - py3-libs depends on python3, and on mypy-requirements.txt
#   - uftrace depends on python3 - is it system python3?
# - other stuff in the release
#   - smoosh tests
#   - spec-compat?

_build-soil-images() {
  # this excludes the test image

  deps/images.sh list soil | while read -r image; do
    deps/images.sh build $image T
  done
}

build-soil-images() {
  time _build-soil-images "$@"
}

push-all-images() {
  deps/images.sh list | xargs --verbose -n 1 -- deps/images.sh push
}

download-for-soil() {
  deps/from-binary.sh download-clang
  deps/from-tar.sh download-wild
}

_soil-all() {
  local resume1=${1:-}
  local resume2=${2:-}
  local resume3=${3:-}
  local resume4=${4:-}
  local resume5=${5:-}

  if test -z "$resume1"; then
    download-for-soil
  fi

  if test -z "$resume2"; then
    build/deps.sh boxed-clean
    # TODO: can also rm-oils-crap and _build/wedge/*

    build/deps.sh fetch
    # 'soil' includes bloaty, uftrace, R-libs
    build/deps.sh boxed-wedges-2025 soil
  fi

  if test -z "$resume3"; then
    # for now, use this /wedge build, because the ../oils.DEPS one has a bug
    # possibly related to uke0 versus uke user
    build/deps.sh boxed-uftrace-OLD
  fi

  if test -z "$resume4"; then
    # build to populate apt-cache
    deps/images.sh build wedge-bootstrap-debian-12
    deps/images.sh build soil-debian-12
  fi

  if test -z "$resume5"; then
    build-soil-images
  fi

  push-all-images
}

soil-all() {
  time _soil-all "$@"
}

soil-all-podman() {
  # deps/wedge.sh respects $DOCKER for wedge builds - needs root now
  # deps/images.sh respects $DOCKER for image builds - rootless

  DOCKER=podman soil-all "$@"
}

task-five "$@"
