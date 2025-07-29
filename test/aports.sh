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
#   $0 checkout-stable
#   $0 download-oils
#
# Build package in chroot:
#
#   $0 make-chroot     # 267 MB, 247 K files
#                      # ncdu shows gcc is big, e.g. cc1plus, cc1, lto1 are each 35-40 MB
#   $0 add-build-deps  # add packages that build packages
#                      # 281 MB, 248 K files
#   $0 config-chroot   # user/groups, keygen
#   $0 oils-in-chroot  # copy-aports: 307 MB, 251 K files
#
#   $0 save-default-config
#   $0 apk-manifest
#
#   $0 fetch-packages fetch 100,300p  # packages 100-300
#   $0 fetch-packages fetch .*        # all packages
#
# Build a config
#   $0 clean                              # remove files from previous run
#   $0 set-osh-as-sh                      # or set-baseline
#   $0 build-packages 100,300p osh-as-sh
#   $0 build-packages '.*'     osh-as-sh  # 310 MB, 251 K files

#   $0 build-many-configs 'shard3'        # build packages 301 to 400
#
#   $0 copy-results osh-as-sh             # copy TSV and abridged logs out of chroot
#
# On localhost:
#   export EPOCH=2025-07-28-100to300
#   test/aports.sh sync-results
#
#   Now see test/aports-html.sh
#
# WARNING: THIS IS ESSENTIAL for RUNNING build-many-configs (but not
# build-packages):
#
# The /etc/sudoers.d needs to be modified so that sudo doesn't EVER
# timeout Otherwise running the second config will prompt for the root password
#
# This is how I did it manually
# $ sudo visudo -f /etc/sudoers.d/no-timeout
#
# $ sudo cat /etc/sudoers.d/no-timeout
# Defaults:andy timestamp_timeout=-1
#
# -1 means it's cached forever

# TODO:
# - epoch could be set on build machine, with $0 copy-results
# - $CHROOT_DIR/oils-aports-config could be 'baseline' 'osh-as-sh'?  For the
#   different machines

# Other commands:
#   $0 remove-chroot

# DIR STRUCTURE
#
# he.oils.pub/
#   ~/git/oils-for-unix/oils/
#     _chroot/aports-build/
#       home/builder/   # TODO: change to uke
#        oils-for-unix/oils/  # guest tools
#          build/
#            py.sh
#          _tmp/
#            aports-guest/
#              baseline/
#                7zip.log.txt
#                7zip.task.tsv
#              osh-as-sh/
#              osh-as-bash/
#     _tmp/aports-build/    # HOST
#       baseline/
#         tasks.tsv         # concatenated .task.tsv
#         log/     
#           7zip.log.txt
#         abridged-log/     # tail -n 1000 ont he log
#           gcc.log.txt
# localhost/
#   ~/git/oils-for-unix/oils/
#     _tmp/aports-build/    # HOST
#       baseline/
#         index.html        # from tasks.tsv
#         tasks.tsv 
#         log/     
#           7zip.log.txt
#         abridged-log/     # tail -n 1000 ont he log
#           gcc.log.txt
#       osh-as-sh/          # from tasks.tsv
#         tasks.tsv
#         log/
#         abridged-log/
#     index.html
#
# Another option: don't bother with abridged-log
# - it makes the diff harder - what if one is abridged, and the other isn't?
# - just make a copy

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

source test/aports-common.sh

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

checkout-stable() {
  # 2025-07-25: commit that matches he.oils.pub
  # TODO: update this to a commit from a stable release branch like 3.22-stable
  # https://alpinelinux.org/releases/
  # But note that there is no branch for 3.22.1?
  pushd ../../alpinelinux/aports
  git checkout 7b59d0c9365e4230e0527ba9de3abd28ee58875d
  git log -n 1
  popd > /dev/null

  echo
  echo

  pushd ../alpine-chroot-install
  # this branch has fixes!  TODO: merge to main branch
  git checkout dev-andy-2
  git log -n 1
  popd > /dev/null
}

clone-aci() {
  # I FORKED this, because this script FUCKED UP my /dev dir and current directory!
  # Sent patches upstream

  pushd ..

  time git clone \
    git@github.com:oils-for-unix/alpine-chroot-install || true

  popd
}

download-oils() {
  local job_id=${1:-9886}  # 2025-07
  local url="https://op.oilshell.org/uuu/github-jobs/$job_id/cpp-tarball.wwz/_release/oils-for-unix.tar"
  wget --no-clobber --directory _tmp "$url"
}

user-chroot() {
  $CHROOT_DIR/enter-chroot -u builder "$@"
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

  time sudo $aci -n -d $PWD/$CHROOT_DIR
}

make-user() {
  $CHROOT_DIR/enter-chroot adduser -D builder || true

  # put it in abuild group
  $CHROOT_DIR/enter-chroot addgroup builder abuild || true
  # 'wheel' is for 'sudo'
  $CHROOT_DIR/enter-chroot addgroup builder wheel || true

  # CHeck the state
  user-chroot sh -c 'whoami; echo GROUPS; groups'
}

setup-doas() {
  # Manual configuration for abuild-keygen

  #sudo cat _chroot/aports-build/etc/doas.conf
  sudo rm -f $CHROOT_DIR/etc/doas.conf

  # no password
  $CHROOT_DIR/enter-chroot sh -c 'echo "permit nopass :wheel" >> /etc/doas.conf'
}

config-chroot() {
  make-user
  setup-doas
  keygen
}

add-build-deps() {
  # Must be done as root; there is no 'sudo'

  # alpine-sdk: abuild, etc.
  # pigz: seems like it's optionally used by abuild - should probably speed
  # things up
  # doas: for abuild-keygen
  # bash python3: for time-tsv
  # findutils: for xargs --process-slot-var
  $CHROOT_DIR/enter-chroot sh -c '
  apk update
  apk add alpine-sdk pigz doas bash python3 findutils
  '

  # $CHROOT_DIR/enter-chroot -u builder bash -c 'echo "hi from bash"'
}

change-perms() {
  # pass any number of args

  # get uid from /home/builder
  local uid
  uid=$(stat -c '%u' $CHROOT_HOME_DIR)
  sudo chown --verbose --recursive $uid "$@"
}

copy-aports() {
  local dest=$CHROOT_HOME_DIR/aports/main/

  sudo mkdir -p $dest
  sudo rsync --archive --verbose \
    ../../alpinelinux/aports/main/ $dest

  change-perms $dest
}

code-manifest() {
  # TODO: need per-file tree shaking of build/py.sh
  local -a build_py=(
    build/py.sh  # to compile time-helper

    build/common.sh
    build/dev-shell.sh
    stdlib/osh/bash-strict.sh
    stdlib/osh/byo-server.sh
    stdlib/osh/task-five.sh
    stdlib/osh/two.sh
  )
  for path in \
    benchmarks/time_.py \
    benchmarks/time-helper.c \
    test/aports-guest.sh \
    "${build_py[@]}"
  do
    echo "$PWD/$path" "$path"
  done
}

multi() {
  ### gah this requires python2

  #~/git/tree-tools/bin/multi "$@";
  local git_dir='../..'
  $git_dir/tree-tools/bin/multi "$@";
}

multi-cp() {
  ### like multi cp, but works without python2

  local dest=$1
  while read -r abs_path rel_path; do
    # -D to make dirs

    # Hack: make everything executable for now
    # I feel like this should be in 'multi cp'

    install -m 755 -v -D --no-target-directory "$abs_path" "$dest/$rel_path"

    # cp -v --parents doesn't work, because it requires a directory arg
  done
}

copy-code() {
  local dest=$CHROOT_HOME_DIR/oils-for-unix/oils
  sudo mkdir -v -p $dest

  code-manifest | sudo $0 multi-cp $dest

  change-perms $dest
}

test-time-tsv() {
  user-chroot sh -c '
  cd oils-for-unix/oils
  pwd
  whoami
  echo ---

  build/py.sh time-helper
  test/aports-guest.sh my-time-tsv-test
  '
}

oils-in-chroot() {
  copy-aports
  copy-code
  test-time-tsv

  copy-oils
  build-oils
}

copy-oils() {
  local dest=$CHROOT_HOME_DIR

  local tar=$PWD/_tmp/oils-for-unix.tar
  pushd $dest
  sudo tar -x < $tar
  popd

  change-perms $dest/oils-for-unix-*
}

keygen() {
  user-chroot sh -c '
  #abuild-keygen -h
  abuild-keygen --append --install
  '
}

apk-manifest() {
  # 1643 files - find a subset to build
  local out=$PWD/_tmp/apk-manifest.txt
  mkdir -p _tmp

  pushd $CHROOT_HOME_DIR/aports/main >/dev/null
  find . -name 'APKBUILD' -a -printf '%P\n' | LANG=C sort | tee $out
  popd >/dev/null
}

build-oils() {
  user-chroot sh -c '
  cd oils-for-unix-*
  ./configure
  _build/oils.sh --skip-rebuild
  doas ./install
  '
}

show-config() {
  $CHROOT_DIR/enter-chroot sh -c '
  ls -l /bin/sh /bin/ash /bin/bash
  '
}

save-default-config() {
  $CHROOT_DIR/enter-chroot sh -c '
  set -x
  dest=/bin/bash.ORIG
  cp /bin/bash $dest
  '
  show-config
}

set-baseline() {
  # ensure we have the default config
  $CHROOT_DIR/enter-chroot sh -c '
  set -x
  ln -s -f /bin/busybox /bin/sh
  ln -s -f /bin/busybox /bin/ash
  cp /bin/bash.ORIG /bin/bash
  '
  show-config
}

set-osh-as-X() {
  local x=$1

  $CHROOT_DIR/enter-chroot sh -c '
  x=$1
  set -x
  if ! test -f /usr/local/bin/oils-for-unix; then
    echo "Build Oils first"
    exit
  fi
  ln -s -f /usr/local/bin/oils-for-unix /bin/$x
  ' dummy0 "$x"
  show-config
}

set-osh-as-sh() {
  set-osh-as-X sh
}

set-osh-as-ash() {
  set-osh-as-X ash
}

set-osh-as-bash() {
  set-osh-as-X bash
}

package-dirs() {
  # lz gives 5 packages: some fail at baseline
  # mpfr4: OSH bug, and big log
  # yash: make sure it doesn't hang
  local package_filter=${1:-'lz|mpfr|yash'}

  local -a prefix

  # 100 means 0 to 100
  if [[ $package_filter =~ ^[0-9]+$ ]]; then
    prefix=( head -n $package_filter )

  # 100,300p means lines 100 to 300
  elif [[ $package_filter =~ ^[0-9]+,[0-9]+p$ ]]; then
    prefix=( sed -n $package_filter )

  elif [[ $package_filter =~ ^shard([0-9]+)$ ]]; then
    # shards of 100 packages

    local shard_num=${BASH_REMATCH[1]}
    #echo shard=$shard_num

    local range
    # shard 0 is 0-99
    # shard 9 is 900 to 999
    # shard 10 is 1000 to 1099
    case $shard_num in
      # sed doesn't like 000,099
      0) range='1,100p' ;;
      *) range="${shard_num}01,$(( shard_num + 1))00p" ;;
    esac

    prefix=( sed -n "$range" )

  else
    prefix=( egrep "$package_filter" )

  fi
   
  "${prefix[@]}" _tmp/apk-manifest.txt | sed 's,/APKBUILD$,,g'
}

do-packages() {
  ### Download sources - abuild puts it in /var/cahe/distfiles
  local action=${1:-fetch}
  local package_filter=${2:-}
  # flags to pass to the inner shell
  local sh_flags=${3:-'-e -u'}  # -u to disable -e

  # 6 seconds for 10 packages
  # There are ~1600 packages
  # So if there are 20 shards, each shard could have 10?

  local -a package_dirs=( $(package-dirs "$package_filter") )

  echo "${dirs[@]}"
  #return

  time user-chroot sh $sh_flags -c '

  action=$1
  shift
  for dir in "$@"; do
    time abuild -r -C aports/main/$dir "$action"
  done
  ' dummy0 "$action" "${package_dirs[@]}"
}

fetch-packages() {
  local package_filter=${1:-}

  # -u means we don't pass -e (and it's non-empty)
  do-packages fetch "$package_filter" '-u'
}

banner() {
  echo
  echo "=== $1"
  echo
}

build-packages() {
  # https://wiki.alpinelinux.org/wiki/Abuild_and_Helpers#Basic_usage
  local package_filter=${1:-}
  local config=${2:-baseline}

  local -a package_dirs=( $(package-dirs "$package_filter") )

  banner "Building ${#package_dirs[@]} packages (filter $package_filter)"

  user-chroot sh -c '
  config=$1
  shift

  cd oils-for-unix/oils
  test/aports-guest.sh build-packages "$config" "$@"
  ' dummy0 "$config" "${package_dirs[@]}"
}

build-many-configs() {
  local package_filter=${1:-}

  # clear credentials first
  sudo -k

  # See note about /etc/sudoers.d at top of file

  for config in baseline osh-as-sh; do

    # this uses enter-chroot to modify the chroot
    # should we have a separate one?  But then fetching packages is different
    set-$config

    # this uses enter-chroot -u
    build-packages "$package_filter" "$config"
  done
}

abridge-logs() {
  local config=${1:-baseline}
  local dest=$BASE_DIR/$config/log

  # local threshold=$(( 1 * 1000 * 1000 ))  # 1 MB
  local threshold=$(( 500 * 1000 ))  # 500 KB

  local guest_dir=$CHROOT_HOME_DIR/oils-for-unix/oils/_tmp/aports-guest/$config 
  local dest_dir=$BASE_DIR/$config/log

  mkdir -v -p $dest_dir

  find $guest_dir -name '*.log.txt' -a -printf '%s\t%P\n' |
  while read -r size path; do
    local src=$guest_dir/$path
    local dest=$dest_dir/$path

    if test "$size" -lt "$threshold"; then
      cp -v $src $dest
    else
      { echo "*** This log is abridged to its last 1000 lines:"; echo; } > $dest
      tail -n 1000 $src >> $dest
    fi
  done

  # From 200 MB -> 96 MB uncompressed
  #
  # Down to 10 MB compressed.  So if we have 4 configs, that's 40 MB of logs,
  # which is reasonable.

  # 500K threshold: 76 MB
  du --si -s $dest_dir
}

copy-results() {
  local config=${1:-baseline}

  #copy-logs "$config"

  abridge-logs "$config"

  local dest=_tmp/aports-build/$config/tasks.tsv
  mkdir -p $(dirname $dest)
  concat-task-tsv "$config" > $dest
}

remove-chroot() {
  # This unmounts /dev /proc /sys/ properly!
  $CHROOT_DIR/destroy --remove
}

chroot-manifest() {
  # TODO: use this to help plan OCI layers
  # 251,904 files after a build of mpfr

  sudo find $CHROOT_DIR -type f -a -printf '%s %P\n'
}

show-chroot() {
  sudo tree $CHROOT_HOME_DIR/oils-for-unix/oils/_tmp
}

clean() {
  # clean chroot
  sudo rm -r -f -v $CHROOT_HOME_DIR/oils-for-unix/oils/_tmp

  # results
  rm -r -f -v $BASE_DIR
}

sizes() {
  set +o errexit

  # 312 MB
  sudo du --si -s $CHROOT_DIR 

  # 29 MB after 80 source packages, that's not so much

  # getting up to 373 M though - worth sharding
  sudo du --si -s $CHROOT_DIR/var/cache

  sudo du --si -s $CHROOT_DIR/var/cache/distfiles

  # 110 MB just of logs
  # need to thin these out
  sudo du --si -s $CHROOT_HOME_DIR/oils-for-unix/oils/_tmp/

  sudo du --si -s $BASE_DIR/
}

task-five "$@"
