#!/usr/bin/env bash
#
# Build Alpine Linux packages: baseline, OSH as /bin/sh, OSH as /bin/bash
# See regtest/aports.md
#
# Usage:
#   regtest/aports-run.sh <function name>
#
# Common usage:
#
#   export APORTS_EPOCH=2025-08-04-foo        # optional override
#   $0 build-many-shards-overlayfs shard{0..16}         # build all 17 shards in 2 configs
#
# Also useful:
#
#   $0 fetch-packages fetch $pkg_filter $a_repo  # alpine repo is 'main' or 'community'
#
#   $0 fetch-packages fetch 100,300p   # packages 100-300
#   $0 fetch-packages fetch '.*'       # all packages
#
# Look for results in _tmp/aports-build/
#
# Build many packages:
#
#   $0 build-packages-overlayfs osh-as-sh shard9 community
#   $0 build-packages-overlayfs osh-as-sh shardA   # main is default $a_repo
#
# Build a single package:
#
#   $0 build-package-overlayfs osh-as-sh userspace-rcu
#   $0 build-package-overlayfs osh-as-sh xterm          community  # community repo
#
# Drop into a shell:
#   INTERACTIVE=1 $0 build-package-overlayfs osh-as-sh userspace-rcu
#
# PKG_FILTER
#   shard[0-9]+      - shard3 is packages 301 to 400
#   [0-9]+           - 42 means build the first 42 packages
#   [0-9]+,[0-9]+p   - 100,300p packages 100 to 300 (sed syntax)
#   ALL              - all packages
#   .*               - egrep pattern matching all packages
#   curl             - egrep pattern matching 'curl'
#
# Preview packages:
#
#   $0 package-dirs shard9 community

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

source regtest/aports-common.sh

#
# Config
#

show-config() {
  enter-rootfs sh -c '
  ls -l /bin/sh /bin/ash /bin/bash
  '
}

set-baseline() {
  # ensure we have the default config
  enter-rootfs sh -c '
  set -x
  ln -s -f /bin/busybox /bin/sh
  ln -s -f /bin/busybox /bin/ash
  cp /bin/bash.ORIG /bin/bash
  '
  show-config
}

set-osh-as-X() {
  local x=$1

  enter-rootfs sh -c '
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
  # lzip: a single fast package
  # mpfr4: OSH bug, and big log
  # yash: make sure it doesn't hang
  local package_filter=${1:-'lz|mpfr|yash'}
  local a_repo=${2:-main}  # or 'community'

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

  # shardA, shardB For testing the combined report
  elif [[ $package_filter =~ ^shard([A-Z]+)$ ]]; then
    local shard_name=${BASH_REMATCH[1]}
    case $a_repo in
      main)
        case $shard_name in
          A) package_filter='^gzip' ;;  # failure
          B) package_filter='^xz' ;;    # failure
          C) package_filter='^lz' ;;    # 3 packages
          D) package_filter='^jq$' ;;   # produces autotools test-suite.log
          E) package_filter='^py3-p' ;;   # many packages in parallel
          F) package_filter='^py3-pathspec' ;;   # very fast package
          P) package_filter='^xz$|^shorewall' ;;   # patches
          *) package_filter='^perl-http-daemon' ;;   # test out perl
        esac
        ;;
      community)
        case $shard_name in
          A) package_filter='^py3-zulip' ;;  # one Python package
          B) package_filter='^xterm' ;;      # one C package
          C) package_filter='^shfmt' ;;      # one Go package
          D) package_filter='^shellspec' ;;  # OSH disagreement because of 'var'
          *) package_filter='^shell' ;;      # a bunch of packages
        esac
        ;;
      *)
        die "Invalid a_repo $a_repo"
        ;;
    esac

    prefix=( egrep "$package_filter" )

  elif [[ $package_filter =~ ^disagree-(.*)+$ ]]; then
    local filename=${BASH_REMATCH[1]}
    # A file of EXACT package names, not patterns
    # See copy-disagree
    local package_file="_tmp/$package_filter.txt"
    comm -1 -2 <(sort $package_file) <(sort _tmp/apk-${a_repo}-manifest.txt)
    return

  else
    prefix=( egrep "$package_filter" )

  fi
   
  "${prefix[@]}" _tmp/apk-${a_repo}-manifest.txt
}

copy-disagree() {
  ### Determine what to run

  local epoch=${1:-2025-09-18-bash}
  cp -v \
    _tmp/aports-report/$epoch/disagree-packages.txt \
    _tmp/disagree-$epoch.txt
}

do-packages() {
  ### Download sources - abuild puts it in /var/cahe/distfiles
  local action=${1:-fetch}
  local package_filter=${2:-}
  local a_repo=${3:-main}
  # flags to pass to the inner shell
  local sh_flags=${4:-'-e -u'}  # -u to disable -e

  # 6 seconds for 10 packages
  # There are ~1600 packages
  # So if there are 20 shards, each shard could have 10?

  local -a package_dirs
  package_dirs=( $(package-dirs "$package_filter" "$a_repo") )

  echo "${dirs[@]}"
  #return

  time enter-rootfs-user sh $sh_flags -c '

  action=$1
  a_repo=$2
  shift 2
  for dir in "$@"; do
    time abuild -r -C aports/$a_repo/$dir "$action"
  done
  ' dummy0 "$action" "$a_repo" "${package_dirs[@]}"
}

fetch-packages() {
  local package_filter=${1:-}
  local a_repo=${2:-main}

  # -u means we don't pass -e (and it's non-empty)
  do-packages fetch "$package_filter" "$a_repo" '-u'
}

banner() {
  echo
  echo "=== $@"
  echo
}

build-package-overlayfs() {
  local config=${1:-baseline}
  local pkg=${2:-lua5.4}
  local a_repo=${3:-main}

  # baseline stack:
  #   _chroot/aports-build
  #   _chroot/package-upper/baseline/gzip    # upper dir / layer dir
  #
  # osh-as-sh stack:
  #   _chroot/aports-build
  #   _chroot/osh-as-sh.overlay/layer        # this has the symlink
  #   _chroot/package-upper/osh-as-sh/gzip   # upper dir / layer dir

  # allow concurrency
  local xargs_slot="${XARGS_SLOT:-99}"
  local ov_base_dir=_chroot/package-slot${xargs_slot}.overlay

  local merged=$ov_base_dir/merged
  local work=$ov_base_dir/work

  local layer_dir=_chroot/package-layers/$config/$pkg
  mkdir -p $merged $work $layer_dir

  local overlay_opts
  case $config in
    baseline)
      overlay_opts="lowerdir=$CHROOT_DIR,upperdir=$layer_dir,workdir=$work"
      ;;
    osh-as-sh)
      local osh_as_sh=_chroot/osh-as-sh.overlay/layer
      overlay_opts="lowerdir=$osh_as_sh:$CHROOT_DIR,upperdir=$layer_dir,workdir=$work"
      ;;
    *)
      die "Invalid config $config"
      ;;
  esac

  # -o index=off fixes this error: fsconfig() failed: Stale file handle
  # See also https://oilshell.zulipchat.com/#narrow/channel/522730-distros/topic/setting.20up.20regtest.2Faports-setup.2Esh/with/544318771
  sudo mount \
    -t overlay \
    aports-package \
    -o "$overlay_opts" \
    -o index=off \
    $merged

  # mount over the overlay, onto the merged
  # https://man7.org/linux/man-pages/man5/procfs.5.html
  sudo mount \
    -t proc \
    "_chroot_proc_${xargs_slot}" $merged/proc

  # https://man7.org/linux/man-pages/man5/sysfs.5.html
  sudo mount \
    -t sysfs \
    "_chroot_sysfs_${xargs_slot}" $merged/sys

  # https://lwn.net/Articles/330985/
  sudo mount \
    -t devtmpfs \
    "_chroot_devtmpfs_${xargs_slot}" $merged/dev

  local -a prefix
  if test -n "${XARGS_SLOT:-}"; then
    local x=$XARGS_SLOT

    # run slot 0 on cores 0 and 1
    # run slot 9 on cores 18 and 19
    local cores="$(( x*2 )),$(( x*2 + 1 ))"

    # oversubscribe
    # run slot 0 on cores 0 and 1
    # run slot 19 on cores 19 and 0
    #local cores="$(( x )),$(( (x + 1) % NUM_CORES ))"
    prefix=( taskset -c "$cores" )
  fi

  "${prefix[@]}" $merged/enter-chroot -u udu sh -c '
  cd oils

  # show the effect of the overlay
  #ls -l /bin/sh

  regtest/aports-guest.sh build-one-package "$@"
  ' dummy0 "$pkg" "$a_repo" "$xargs_slot"

  if test -n "$INTERACTIVE"; then
    echo "Starting interactive shell in overlayfs environment for package $a_repo/$pkg"
    echo "Rebuild: abuild -f -r -C ~/aports/$a_repo/$pkg -k -K"
    echo "   Help: abuild -h"
    # If the last command in the child shell exited non-zero then ctrl-d/exit
    # will report that error code to the parent. If we don't ignore that error
    # we will exit early and leave the package overlay mounted.
    set +o errexit
    $merged/enter-chroot -u udu
    set -o errexit
  fi

  unmount-loop $merged/proc
  unmount-loop $merged/sys
  unmount-loop $merged/dev
  unmount-loop $merged
}

build-pkg() {
  ### trivial wrapper around build-package-overlayfs - change arg order for xargs
  local config=${1:-baseline}
  local a_repo=${2:-main}
  local pkg=${3:-lua5.4}

  build-package-overlayfs "$config" "$pkg" "$a_repo"

  # TODO:
  # - we should only do this after we've done BOTH configs, so it appears
  #   atomically
  save-package-files $config $a_repo $pkg

  # TODO: blow away the layer dir, since we saved the "tombstone".
  # We're not doing this now because we're still reporting off DEPRECATED shard
  # files.
}

LOG_SIZE_THRESHOLD=$(( 500 * 1000 ))  # 500 KB
#LOG_SIZE_THRESHOLD=$(( 1 * 1000 ))

abridge-one-log() {
  local src=$1
  local dest=$2

  local size
  size=$(stat --format '%s' $src)
  if test $size -lt $LOG_SIZE_THRESHOLD; then
    #cp --verbose $src $dest
    cp $src $dest
  else
    # Bug fix: abridging to 1000 lines isn't sufficient.  We got some logs
    # that were hundreds of MB, with less than 1000 lines!
    { echo "*** This log is abridged to its last $LOG_SIZE_THRESHOLD bytes"
      echo
      tail --bytes $LOG_SIZE_THRESHOLD $src
    } > $dest
  fi
}

# save-package-files creates a tree we can rsync
# For EACH PACKAGE, without shards
#
# TODO: Both baseline and osh-as-sh should appear atomically?

# Source tree:
#
# _chroot/package-layers/
#   baseline/
#     jq/
#       home/udu/
#         oils/_tmp/aports-guest/
#           jq.log.txt
#           jq.task.tsv
#         packages/main/x86_64
#           jq-*.apk
#         aports/main/jq/
#           src/jq-1.8.0/test-suite.log
#
# _tmp/aports-build/ 
#   2025-11-12/
#     shard0/   # TODO: remove shards
#       baseline/
# NEW:
#         apk/
#           jq.apk.txt        # md5sum
#         layer/
#           jq.tombstone.txt  # find '%s %P\n'
#         task/
#           jq.task.tsv
# EXISTING:
#         apk.txt
#         tasks.tsv
#         log/
#           jq.log.txt
#         test-suite/
#           jq/  TODO: support multiple logs
#             test-suite.log 

save-package-files() {
  ### Copy some files from _chroot/package-layers/ -> _tmp/aports-build

  local config=${1:-baseline}
  local a_repo=${2:-main}
  local pkg=${3:-jq}

  local layer_dir=_chroot/package-layers/$config/$pkg
  local dest_dir=$BASE_DIR/$APORTS_EPOCH/$config

  # 5 directories
  mkdir -p $dest_dir/{apk,layer,task,log,test-suite}

  cp \
    $layer_dir/home/udu/oils/_tmp/aports-guest/$pkg.task.tsv \
    $dest_dir/task

  abridge-one-log \
    $layer_dir/home/udu/oils/_tmp/aports-guest/$pkg.log.txt \
    $dest_dir/log/$pkg.log.txt

  # Abridge this log too
  { find $layer_dir/home/udu/aports/$a_repo/$pkg -name 'test-suite.log' 2> /dev/null || true; } |
  while read -r log_src; do
    local test_suite_dest_dir=$dest_dir/test-suite/$pkg
    mkdir -p $test_suite_dest_dir
    abridge-one-log \
      $log_src \
      $test_suite_dest_dir/test-suite.log.txt
  done

  md5sum $layer_dir/home/udu/packages/$a_repo/x86_64/*.apk \
    > $dest_dir/apk/$pkg.apk.txt 2> /dev/null || true  # allow failure if nothing built

  # Truncate large listings - e.g. clang packages have over 120K files
  { find $layer_dir -printf '%s %P\n' 2> /dev/null || true; } |
    head -n 1000 > $dest_dir/layer/$pkg.tombstone.txt 

  #tree $dest_dir

  # log.txt
  # log.txt
}

NUM_CORES=$(( $(nproc) ))

# 2 cores per package build
NUM_PAR=$(( NUM_CORES / 2 ))

# over-subscribe - allow 20 processes to see 2 cores each
# Note: this causes more timeouts.  TODO: get rid of shards to get rid of
# stragglers, and then raise the timeout to 20 minutes or more.
# NUM_PAR=$(( NUM_CORES ))

# TODO: we ran into the env.sh race condition in the enter-chroot script
# generated by alpine-chroot-install
build-many-packages-overlayfs() {
  local package_filter=${1:-}
  local config=${2:-baseline}
  local a_repo=${3:-main}
  local parallel=${4:-T}

  banner "Building packages (filter=$package_filter a_repo=$a_repo)"

  local -a flags
  if test -n "$parallel"; then
    log "(with $NUM_PAR jobs in parallel)"
    flags=( -P $NUM_PAR )
  else
    log '(serially)'
  fi

  package-dirs "$package_filter" $a_repo |
    xargs "${flags[@]}" -n 1 --process-slot-var=XARGS_SLOT -- \
    $0 build-pkg $config $a_repo
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

APORTS_EPOCH="${APORTS_EPOCH:-}"
# default epoch
if test -z "$APORTS_EPOCH"; then
  APORTS_EPOCH=$(date '+%Y-%m-%d')
fi

_build-many-configs-overlayfs() {
  local package_filter=${1:-}
  local epoch=${2:-$APORTS_EPOCH}
  local a_repo=${3:-main}

  if test -z "$package_filter"; then
    die "Package filter is required (e.g. shard3, ALL)"
  fi

  clean-guest

  # See note about /etc/sudoers.d at top of file

  local dest_dir="$BASE_DIR/$epoch/$package_filter"  # e.g. shard10

  for config in "${CONFIGS[@]}"; do
    banner "$epoch: Using config $config"

    build-many-packages-overlayfs "$package_filter" "$config" "$a_repo"
  done
}

remove-shard-files() {
  local shard_dir=${1:-_chroot/shardC}

  # For all packages packages, for baseline and osh-as-sh, clean up the aports source dir
  # For linux, clang, etc. it becomes MANY GIGABYTES
  # 
  # 2025-09-12: ignore errors from rm; I think there was a race condition -
  # processes could still be running and creating files
  #
  # rm: cannot remove '_chroot/shard6/baseline/llvm19/home/udu/aports/main/llvm19/src/llvm-project-19.1.7.src/build/lib': Directory not empty
  # real    1041m46.464s

  #log "Removing big files in shard $shard_dir"
  #sudo rm -r -f $shard_dir/*/*/home/udu/aports/ || true

  log "Removing all files in $shard_dir"
  sudo rm -r -f $shard_dir || true
}

build-many-shards-overlayfs() {
  sudo -k

  local a_repo=${A_REPO:-main}  # env var like $APORTS_EPOCH

  # Clean up old runs
  sudo rm -r -f _chroot/package-layers _chroot/shard* _chroot/disagree*

  banner "$APORTS_EPOCH $a_repo: building shards: $*"

  time for shard_name in "$@"; do
    _build-many-configs-overlayfs "$shard_name" "$APORTS_EPOCH" "$a_repo"

    # Move layer files to _chroot/shard10/{baseline,osh}/...
    mv -v --no-target-directory _chroot/package-layers _chroot/$shard_name

    # Make it rsync-able in _tmp/aports-build ($BASE_DIR)
    make-shard-tree $shard_name $a_repo

    # Remove big files
    remove-shard-files _chroot/$shard_name

    # TODO: we should publish and clean up after every PACKAGE, rather than
    # each shard
  done
}

build-and-proc-log() {
  # Measure resource utilization
  local proc_dir="$BASE_DIR/$APORTS_EPOCH/proc-log"
  mkdir -v -p $proc_dir
  regtest/proc_log.py --out-dir $proc_dir --sleep-secs 5 &
  local proc_log_pid=$!

  sleep 0.05  # prevent overlapping sudo prompt

  build-many-shards-overlayfs "$@"

  kill -s TERM $proc_log_pid
  wc -l $proc_dir/*.txt
}

make-shard-tree() {
  ### Put outputs in rsync-able format, for a SINGLE shard

  # The dir structure is like this:
  #
  # _tmp/aports-build/
  #   2025-09-10-overlayfs/
  #     shard0/
  #       baseline/
  #         apk.txt
  #         tasks.tsv
  #         log/
  #           gzip.log.txt
  #           xz.log.txt
  #         test-suite/  # autotools dir
  #           gzip/
  #             test-suite.log.txt
  #       osh-as-sh/
  #         apk.txt
  #         tasks.tsv
  #         log/
  #           gzip.log.txt
  #           xz.log.txt
  #         test-suite/
  #           gzip/
  #             test-suite.log.txt
  #     shard1/
  #       ...
  #     shard16/
  #       ...

  local shard_name=$1
  local a_repo=${2:-main}
  local epoch=${3:-$APORTS_EPOCH}

  local shard_dir=_chroot/$shard_name

  for config in baseline osh-as-sh; do
    local dest_dir=$BASE_DIR/$epoch/$shard_name/$config
    mkdir -p $dest_dir
    #ls -l $shard_dir/$config

    # Four outputs
    # 1) log.txt for each package
    # 2) Optional test-suite.txt for each package
    # 3) merged tasks.tsv
    #    - comes from .task.tsv
    # 4) merged apk.txt
    #
    # So 3 and 4 should not be merged yet
    #
    # _tmp/aports-build/
    #   2025-11-12/
    #     shardP/
    #       baseline/
    #         log/
    #         test-suite/
    #         apk.txt
    #         tasks.tsv
    #
    # We want to

    time python3 devtools/tsv_concat.py \
      $shard_dir/$config/*/home/udu/oils/_tmp/aports-guest/*.task.tsv > $dest_dir/tasks.tsv

    # Allowed to fail if zero .apk are built
    time md5sum $shard_dir/$config/*/home/udu/packages/$a_repo/x86_64/*.apk \
      > $dest_dir/apk.txt 2> /dev/null || true

    abridge-logs $shard_dir/$config $dest_dir

  done
}

abridge-logs() {
  local config_src_dir=${1:-_chroot/shardD/osh-as-sh}
  local dest_dir=${2:-$BASE_DIR/shardD/osh-as-sh}

  local log_dest_dir=$dest_dir/log
  local test_suite_dest_dir=$dest_dir/test-suite
  mkdir -p $log_dest_dir $test_suite_dest_dir

  local threshold=$(( 500 * 1000 ))  # 500 KB

  # this assumes the build process doesn't create *.log.txt
  # test-suite.log is the name used by the autotools test runner - we want to save those too
  # ignore permission errors with || true
  { find $config_src_dir -name '*.log.txt' -a -printf '%s\t%P\n' 2> /dev/null || true; } |
  while read -r size path; do
    local src=$config_src_dir/$path
    # Remove text until last slash (shortest match)
    # like $(basename $path) but in bash, for speed
    local filename=${path##*/}
    local dest=$log_dest_dir/$filename

    if test "$size" -lt "$threshold"; then
      cp -v $src $dest
    else
      # Bug fix: abriding to 1000 lines isn't sufficient.  We got some logs
      # that were hundreds of MB, with less than 1000 lines!
      { echo "*** This log is abridged to its last 500 KB:"
        echo
        tail --bytes 500000 $src
      } > $dest
    fi
  done

  { find $config_src_dir -name 'test-suite.log' -a -printf '%P\n' 2> /dev/null || true; } |
  while read -r path; do
    local src=$config_src_dir/$path

    # Remove text after the first slash (shortest match)
    local package_name=${path%%/*}
    local dest=$test_suite_dest_dir/$package_name/test-suite.log.txt

    mkdir -p "$(dirname $dest)"
    cp -v --no-target-directory $src $dest
  done

  # 500K threshold: 76 MB
  du --si -s $log_dest_dir
}

demo-build() {
  local pkg=${1:-gzip}  # in shardA, uses many cores
  local do_pin=${2:-}

  local -a prefix
  if test -n "$do_pin"; then
    echo "*** Pinning to CPU 0 ***"
    prefix=( taskset -c 0 )
  fi

  "${prefix[@]}" $CHROOT_DIR/enter-chroot -u udu sh -c '
  pkg=$1

  echo "nproc = $(nproc)"

  cd oils
  set -x

  # Note the user / real ratio!  How many cores did we use?
  time regtest/aports-guest.sh build-one-package $pkg
  ' dummy0 $pkg
}

test-taskset() {
  local pkg=${1:-gzip}  # in shardA, uses many cores

  demo-build $pkg ''
  demo-build $pkg T
}

test-proc-log() {
  local out_dir=_tmp/proc-log
  mkdir -p $out_dir

  regtest/proc_log.py --out-dir $out_dir &
  local pid=$!
  sleep 3.1  # should get 3 entries
  kill $pid
  wc -l $out_dir/*.txt
}

task-five "$@"
