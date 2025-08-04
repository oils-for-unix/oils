#!/usr/bin/env bash
#
# Build Alpine Linux packages: baseline, OSH as /bin/sh, OSH as /bin/bash
#
# Usage:
#   regtest/aports-run.sh <function name>
#
# Examples:
#
#   $0 fetch-packages fetch PKG_FILTER
#
#   $0 fetch-packages fetch 100,300p   # packages 100-300
#   $0 fetch-packages fetch '.*'       # all packages
#
# Common usage:
#
#   export APORTS_EPOCH=2025-08-04-foo        # optional override
#   $0 build-many-shards shard{0..16}         # build all 17 shards in 2 configs
#
# Look for results in _tmp/aports-build/
#
# More fine-grained builds
#
#   $0 build-many-configs PKG_FILTER          # build a single shard
#                                             # e.g. 'shard3': build packages 301 to 400
#
# Build an individual config:
#   $0 set-osh-as-sh                          # or set-baseline
#   $0 build-packages PKG_FILTER osh-as-sh
#   $0 build-packages '.*'       osh-as-sh    # 310 MB, 251 K files
#
# PKG_FILTER
#   shard[0-9]+      - shard3 is packages 301 to 400
#   [0-9]+           - 42 means build the first 42 packages
#   [0-9]+,[0-9]+p   - 100,300p packages 100 to 300 (sed syntax)
#   ALL              - all packages
#   .*               - egrep pattern matching all packages
#   curl             - egrep pattern matching 'curl'
#
# Now run regtest/aports-html.sh on localhost, e.g.
#
#   regtest/aports-html.sh sync-results

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

source regtest/aports-common.sh

#
# Config
#

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

#
# Run
#

package-dirs() {
  # lz gives 5 packages: some fail at baseline
  # mpfr4: OSH bug, and big log
  # yash: make sure it doesn't hang
  local package_filter=${1:-'lz|mpfr|yash'}

  local -a prefix

  if [[ $package_filter = 'ALL' ]]; then
    prefix=( cat )

  # 100 means 0 to 100
  elif [[ $package_filter =~ ^[0-9]+$ ]]; then
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

  cd oils
  regtest/aports-guest.sh build-packages "$config" "$@"
  ' dummy0 "$config" "${package_dirs[@]}"
}

clean-host-and-guest() {
  # host dir _tmp/aports-build
  rm -r -f -v $BASE_DIR
}

clean-guest() {
  # clean guest chroot
  sudo rm -r -f -v $CHROOT_HOME_DIR/oils/_tmp
}

readonly -a CONFIGS=( baseline osh-as-sh ) 

abridge-logs() {
  local config=${1:-baseline}
  local dest_dir=$2

  # local threshold=$(( 1 * 1000 * 1000 ))  # 1 MB
  local threshold=$(( 500 * 1000 ))  # 500 KB

  local guest_dir=$CHROOT_HOME_DIR/oils/_tmp/aports-guest/$config 

  local log_dir="$dest_dir/$config/log"
  mkdir -v -p $log_dir

  find $guest_dir -name '*.log.txt' -a -printf '%s\t%P\n' |
  while read -r size path; do
    local src=$guest_dir/$path
    local dest=$log_dir/$path

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
  local config=$1
  local dest_dir=$2

  #copy-logs "$config"

  abridge-logs "$config" "$dest_dir"

  local dest=$dest_dir/$config/tasks.tsv
  mkdir -p $(dirname $dest)
  concat-task-tsv "$config" > $dest
}

APORTS_EPOCH="${APORTS_EPOCH:-}"
# default epoch
if test -z "$APORTS_EPOCH"; then
  APORTS_EPOCH=$(date '+%Y-%m-%d')
fi

_build-many-configs() {
  local package_filter=${1:-}
  local epoch=${2:-$APORTS_EPOCH}

  if test -z "$package_filter"; then
    die "Package filter is required (e.g. shard3, ALL)"
  fi

  clean-guest

  # See note about /etc/sudoers.d at top of file

  for config in "${CONFIGS[@]}"; do
    # this uses enter-chroot to modify the chroot
    # should we have a separate one?  But then fetching packages is different
    banner "$epoch: Set config to $config"
    set-$config

    # this uses enter-chroot -u
    build-packages "$package_filter" "$config"
  done

  local dest_dir="$BASE_DIR/$epoch/$package_filter"
  for config in "${CONFIGS[@]}"; do
    copy-results "$config" "$dest_dir"
  done
}

build-many-configs() {
  # clear credentials first
  sudo -k

  _build-many-configs "$@"
}

build-many-shards() {
  sudo -k

  banner "$APORTS_EPOCH: building shards: $@"

  for package_filter in "$@"; do
    _build-many-configs "$package_filter" "$APORTS_EPOCH"
  done
}

task-five "$@"
