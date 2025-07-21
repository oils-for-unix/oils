#!/usr/bin/env bash
#
# Build Alpine Linux packages: baseline, OSH as /bin/sh, OSH as /bin/bash
#
# Usage:
#   test/aports.sh <function name>
#
# Setup:
#   $0 clone-aports
#   $0 clone-aci
#
# Build package in chroot:
#
#   $0 make-chroot - 267 MB, 247 K files
#                    ncdu shows gcc is big, e.g. cc1plus, cc1, lto1 are each 35-40 MB
#   $0 make-user
#   $0 setup-doas
#   $0 add-build-deps  # add packages that build packages
#                      # 281 MB, 248 K files
#   $0 copy-aports     # 307 MB, 251 K files
#   $0 keys
#   $0 build-packages  # 310 MB, 251 K files - hm did it clean up after itself?
#   $0 remove-chroot

# SHARDING of sources
#
# fetch sizes:
#   20 packages - 403 MB after
#   40 packages - 404 MB after
#   60 packages - 408 MB after
#   80 packages - 422 MB after
#
# OK so these packages aren't that big
# They should be baked in once though.  Not built on every run.
# - Should I manually shard /var/cache then?  Hm

# builddeps sizes
#   10 packages - 588 MB
#   20 packages - 646 MB
#
#   Oof that is a lot!  May be tougher to get on Github Actions
#   Well we don't have to pre-bake it, I guess we can download it the CDN

# Error
# ERROR: unable to select packages:
#   apk-tools-2.14.9-r2:
#     breaks: .makedepends-abuild-20250721.005129[apk-tools>=3.0.0_rc4]
#     satisfies: world[apk-tools] abuild-3.15.0-r0[apk-tools>=2.0.7-r1] .makedepends-acf-apk-tools-20250721.004934[apk-tools]
#   .makedepends-abuild-20250721.005129:
#     masked in: cache
#     satisfies: world[.makedepends-abuild=20250721.005129]

# TODO:
# - build many packages at once - make a list

# CI Job
#
# - Inputs
#   - Shell config: baseline, osh-as-sh, osh-as-bash
#   - Shard Number - this affects the container?
# - Outputs
#   - TSV file, log files, and HTML, like build/deps.sh (dev-setup-*)
#   - Performance info
#   - Do we want to expose the actual packages?

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

clone-aports() {
  local dir=../../alpinelinux

  mkdir -p $dir
  pushd $dir

  # Took 1m 13s, at 27 MiB /ssec
  time git clone \
    https://gitlab.alpinelinux.org/alpine/aports.git
    #git@gitlab.alpinelinux.org:alpine/aports.git || true

  popd
}

clone-aci() {
  # I FORKED this, because this script FUCKED UP my /dev dir and current directory!
  # Sent patches upstream

  pushd ..

  time git clone \
    git@github.com:oils-for-unix/alpine-chroot-install || true

  pushd alpine-chroot-install
  # this branch has fixes!  TODO: merge to main branch
  git checkout dev-andy-2
  popd

  popd
}

download-oils() {
  local job_id=${1:-9886}  # 2025-07
  local url="https://op.oilshell.org/uuu/github-jobs/$job_id/cpp-tarball.wwz/_release/oils-for-unix.tar"
  wget --no-clobber --directory _tmp "$url"
}

make-chroot() {
  local aci='../alpine-chroot-install/alpine-chroot-install'

  $aci --help

  # Notes:
  # - $aci -d requires an ABSOLUTE path.  With a relative path, it creates
  # _chroot/aports-build/_chroot/aports-build Filed bug upstream.
  # - The -n flag is a feature I added: do not mount host dirs
  # - TODO: when you run it twice, it should abort if the directory is full
  # - Takes ~8 seconds

  # default packages: build-base ca-certificates ssl_client
  #
  # This is already 267 MB, 247 K files

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

  #_chroot/aports-build/enter-chroot sh -c 'apk update; apk add bash abuild alpine-sdk doas'

  # alpine-sdk: abuild, etc.
  _chroot/aports-build/enter-chroot sh -c 'apk update; apk add alpine-sdk doas'

  #_chroot/aports-build/enter-chroot -u builder bash -c 'echo "hi from bash"'
}

readonly CHROOT_DIR=_chroot/aports-build
readonly CHROOT_HOME_DIR=$CHROOT_DIR/home/builder

copy-aports() {
  local dest=$CHROOT_HOME_DIR/aports/main/

  sudo mkdir -p $dest
  sudo rsync --archive --verbose \
    ../../alpinelinux/aports/main/ $dest

  # get uid from /home/builder
  local uid
  uid=$(stat -c '%u' $CHROOT_HOME_DIR)
  sudo chown --verbose --recursive $uid $dest
}

copy-oils() {
  local dest=$CHROOT_HOME_DIR

  local tar=$PWD/_tmp/oils-for-unix.tar
  pushd $dest
  sudo tar -x < $tar
  popd

  local uid
  uid=$(stat -c '%u' $CHROOT_HOME_DIR)
  sudo chown --verbose --recursive $uid $dest/oils-for-unix-*
}

keys() {
  $CHROOT_DIR/enter-chroot -u builder sh -c '
  #abuild-keygen -h
  abuild-keygen --append --install
  '
}

apk-manifest() {
  # 1643 files - find a subset to build
  local out=$PWD/_tmp/apk-manifest.txt
  mkdir -p _tmp

  pushd $CHROOT_HOME_DIR >/dev/null
  find aports -name 'APKBUILD' | LANG=C sort | tee $out
  popd >/dev/null
}

build-oils() {
  $CHROOT_DIR/enter-chroot -u builder sh -c '
  cd oils-for-unix-*
  ./configure
  _build/oils.sh --skip-rebuild
  doas ./install
  '
}

set-oils-bin-sh() {
  $CHROOT_DIR/enter-chroot sh -c '
  set -x
  mv /bin/sh /bin/sh.OLD
  mv /usr/local/bin/oils-for-unix /bin/sh
  /bin/sh --version
  '
}

do-packages() {
  ### Download sources - abuild puts it in /var/cahe/distfiles
  local action=${1:-fetch}
  local n=${2:-10}

  # 6 seconds for 10 packages
  # There are ~1600 packages
  # So if there are 20 shards, each shard could have 10?

  local dirs
  dirs=( $(head -n $n _tmp/apk-manifest.txt) )
  echo len "${#dirs[@]}"

  if test "${#dirs[@]}" = 0; then
    echo FAIL
    return
  fi

  # strip off APKBUILD
  dirs=( "${dirs[@]%'/APKBUILD'}" )

  echo "${dirs[@]}"
  #return

  time $CHROOT_DIR/enter-chroot -u builder sh -c '
  set -e

  action=$1
  shift
  for dir in "$@"; do
    time abuild -r -C $dir "$action"
  done
  ' dummy0 "$action" "${dirs[@]}"
}

build-packages() {
  # https://wiki.alpinelinux.org/wiki/Abuild_and_Helpers#Basic_usage

  local -a dirs=( aports/main/lua5.2 aports/main/mpfr4 )

  $CHROOT_DIR/enter-chroot -u builder sh -c '
  for dir in "$@"; do
    abuild -r -C $dir

    # -f force
    #abuild -r -f -C $dir
  done
  ' dummy0 "${dirs[@]}"

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

sizes() {
  set +o errexit

  # 312 MB
  sudo du --si -s $CHROOT_DIR 

  # 29 MB after 80 source packages, that's not so much

  # getting up to 373 M though - worth sharding
  sudo du --si -s $CHROOT_DIR/var/cache

  sudo du --si -s $CHROOT_DIR/var/cache/distfiles
}

chroot-manifest() {
  # 251,904 files after a build of mpfr
  sudo find _chroot/aports-build -type f -a -printf '%s %P\n'
}

# Note:
# - /var/cache is 5.8 GB after fetching all sources for Alpine main
# - All APKG packages are 6.9 GB, according to APKINDEX

download-apk-index() {
  wget --no-clobber --directory _tmp \
    http://dl-cdn.alpinelinux.org/alpine/v3.22/main/x86_64/APKINDEX.tar.gz
}

apk-stats() {
  #tar --list -z < _tmp/APKINDEX.tar.gz

  # 5650 packages
  grep 'S:' _tmp/APKINDEX | wc -l

  gawk -f test/aports.awk < _tmp/APKINDEX
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
