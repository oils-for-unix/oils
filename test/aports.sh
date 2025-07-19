#!/usr/bin/env bash
#
# Usage:
#   test/aports.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

clone-aports() {
  local dir=../../alpinelinux

  pushd $dir

  # Took 1m 13s, at 27 MiB /ssec
  time git clone \
    git@gitlab.alpinelinux.org:alpine/aports.git || true

  # WARNING: THIS SCRIPT FUCKED UP MY 
  #
  # /dev
  # current directory!
  #
  # Because I did rm -rf /alpine
  #
  # Should patch upstream, or DO NOT use it.

  time git clone \
    https://github.com/alpinelinux/alpine-chroot-install || true

  popd
}

# TODO:
# - make a regular non-root user
# - build a package with plain 'abuild'?
# - install abuild-rootbld ?
# - install buildrepo?
#
# Then 
# - install OSH as /bin/sh
# - install OSH as /bin/bash
#   - I guess you install the bash package

task-five "$@"
