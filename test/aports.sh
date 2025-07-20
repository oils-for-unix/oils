#!/usr/bin/env bash
#
# Usage:
#   test/aports.sh <function name>
#
# Examples:
#   $0 clone-aports
#   $0 clone-ci
#   $0 make-chroot
#   $0 make-user
#   $0 setup-doas
#   $0 add-build-deps  # packages to build packages
#   $0 copy-aports
#   $0 keys
#   $0 build-packages
#   $0 remove-chroot

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

clone-aports() {
  local dir=../../alpinelinux

  pushd $dir

  # Took 1m 13s, at 27 MiB /ssec
  time git clone \
    git@gitlab.alpinelinux.org:alpine/aports.git || true

  popd
}

clone-aci() {
  # I FORKED this, because this script FUCKED UP my /dev dir and current directory!
  # Sent patches upstream

  pushd ..

  time git clone \
    git@github.com:oils-for-unix/alpine-chroot-install || true

  pushd alpine-chroot-install
  git checkout dev-andy
  popd

  popd
}

make-chroot() {
  local aci='../alpine-chroot-install/alpine-chroot-install'

  $aci --help

  set -x

  # -n: do not mount host dirs (a feature I added)

  # Note: Requires ABSOLUTE path.
  # With relative path, it creates _chroot/aports-build/_chroot/aports-build
  # Filed bug upstream.
  # More TODO: when you run it twice, it should abort if the directory is full

  # Takes ~8 seconds
  time sudo $aci -n -d $PWD/_chroot/aports-build
}

make-user() {
  _chroot/aports-build/enter-chroot adduser -D builder || true

  # put it in abuild group
  _chroot/aports-build/enter-chroot addgroup builder abuild || true
  # 'wheel' is for 'sudo'
  _chroot/aports-build/enter-chroot addgroup builder wheel || true

  # CHeck the state
  _chroot/aports-build/enter-chroot -u builder sh -c 'whoami; echo GROUPS; groups'
}

setup-doas() {
  # Manual configuration for abuild-keygen

  #sudo cat _chroot/aports-build/etc/doas.conf
  sudo rm -f _chroot/aports-build/etc/doas.conf

  # no password
  _chroot/aports-build/enter-chroot sh -c 'echo "permit nopass :wheel" >> /etc/doas.conf'
}

add-build-deps() {
  # Must be done as root; there is no 'sudo'
  # doas: for abuild-keygen?
  _chroot/aports-build/enter-chroot sh -c 'apk update; apk add bash abuild alpine-sdk doas'
  _chroot/aports-build/enter-chroot -u builder bash -c 'echo "hi from bash"'
}

copy-aports() {
  local dest=_chroot/aports-build/home/builder/aports/main/

  sudo mkdir -p $dest
  sudo rsync --archive --verbose \
    ../../alpinelinux/aports/main/ $dest

  # get uid from /home/builder
  local uid
  uid=$(stat -c '%u' _chroot/aports-build/home/builder/)
  sudo chown --verbose --recursive $uid $dest
}

keys() {
  _chroot/aports-build/enter-chroot -u builder bash -c '
  #abuild-keygen -h
  abuild-keygen --append --install
  '
}

build-packages() {
  # Hm says abuild -r
  # https://wiki.alpinelinux.org/wiki/Abuild_and_Helpers#Basic_usage
  #
  # But Claude gave me abuild -F deps unpack

  _chroot/aports-build/enter-chroot -u builder bash -c '
  # Try building lua
  #dir=aports/main/lua5.2
  dir=aports/main/mpfr4

  ls -l $dir

  pushd $dir
  abuild -r
  popd

  exit
  '
  return

  # Other commands
  abuild --help

  ls -l /var/cache
  ls -l /var/cache/distfiles

  #abuild fetch #verify
  #abuild unpack
  #abuild build -r

  #abuild -F deps unpack prepare build install package
  abuild-keygen -h
  newapkbuild -h
  #apkbuild-pypi -h
  buildrepo -h
}

remove-chroot() {
  # This unmounts /dev /proc /sys/ properly!
  _chroot/aports-build/destroy --remove
}

# Notes:
# - buildrepo.lua is a lua script in lua-aports
# - abuild rootbld uses a fresh bubblewrap container for each package?  I want
# to avoid it for now
#
# Then 
# - install OSH as /bin/sh
# - install OSH as /bin/bash
#   - install the bash package first

# More ideas
#
# - Create an OCI image with podman
#   - can you "shard" the aports/main directory into 3?
#   - well it's 27 MB, so it's not that bad
#
# - Separate downloading and building, network and computation
#   - add to 'enter-chroot' a --network none flag
#   - so you can reason about resource usage and time
#
# - add time-tsv
#    - Measure CPU, memory, etc. of each package individually
#   - like build/deps.sh - make a huge table of the times, and failure
#   - highlight failing tasks in RED
#     - and then link to LOGS
#
# - publish logs where?
#   - as .wwz files?
#
# Github Actions
#
# - can we make a separate github actions repo?
#   - oils-for-unix/aports-build
#   - 20 concurrent jobs per USER who started the repo
# - Just Use Github web hook
#   - And optionally run self-hosted RUNNER on he.oils.pub!
#   - he.oils.pub - has 20 CPUs, while Github Actions runners have 4 CPUs
#
# https://docs.github.com/en/actions/reference/actions-limits#job-concurrency-limits-for-github-hosted-runners
# - hm 20 concurrent jobs
#
# 24 hours to build alpine/main
# - does that mean just 1 hour to build on 20 machines?  Could try that
# - and it would be cool if it can show progress in the meantime

# Alpine mirror?
# - https://claude.ai/chat/9ede43a4-1cb1-4e81-be5a-159cd0f9c64e
# - this answer says dl-cdn.alpinelinux.org uses Fastly CDN with GeoDNS, so we
# don't need to change it

# - different providers
#   - gitlab, circle CI
#   - https://depot.dev/pricing - $20/month ulimited concurrency
#   - but 2000 minutes?  That's only 33 hours
# - Burstiness
#   - AWS Fargate Containers - hm doesn't seem to cheap, could be $2.37 per run for 24 hours

task-five "$@"
