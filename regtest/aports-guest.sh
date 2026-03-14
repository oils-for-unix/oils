#!/usr/bin/env bash
#
# Code that runs inside Alpine chroot.
#
# Usage:
#   regtest/aports-guest.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

log() {
  echo "$@" >& 2
}

# copied from build/deps.sh
my-time-tsv() {
  python3 benchmarks/time_.py \
    --tsv \
    --time-span --rusage \
    "$@"
  # TODO: could add --rusage-2 to measure page faults / context switches
  # for tuning the xargs -P value - for thrashing and so forth
}

my-time-tsv-test() {
  # Doesn't output to stdout
  # my-time-tsv sleep 0.5

  my-time-tsv -o /tmp/my-time sleep 0.5
  cat /tmp/my-time
}

readonly LOG_DIR=_tmp/aports-guest

timestamp() {
  date '+%H:%M:%S'
}

build-one-package() {
  # Copied from build/deps.sh maybe-install-wedge
  #
  # Difference vs. build-package: do not need $config here

  local pkg=${1:-lua5.4}
  local a_repo=${2:-main}
  local xargs_slot=${3:-99}  # recorded in tasks.tsv
  # -k: keep built packages
  # -K: keep build time temp files
  local more_abuild_flags=${4:-'-k -K'} 
  local timeout_secs=${5:-$(( 15 * 60 ))}  # 15 minutes by default

  printf -v xargs_str '%2s' $xargs_slot
  echo "  TASK  $xargs_str  $(timestamp)  $pkg"

  local task_file=$LOG_DIR/$pkg.task.tsv
  local log_file=$LOG_DIR/$pkg.log.txt

  mkdir -p $(dirname $task_file)

  my-time-tsv --print-header \
    --field xargs_slot \
    --field pkg \
    --field pkg_HREF \
    --output $task_file

  # DISABLE rootbld for now - bwrap doesn't work inside chroot, because user
  # namespaces don't compose with chroots
  local -a cmd=( abuild -f -r -C ~/aports/$a_repo/$pkg $more_abuild_flags )

  # Give it 1 second to respond to SIGTERM, then SIGKILL
  local -a timeout_cmd=( timeout -k 1 $timeout_secs "${cmd[@]}" )

  #set -x
  # NOTE: log/foo.log.txt is the relative path after copy-results; sync-results
  set +o errexit
  my-time-tsv \
    --field "$xargs_slot" \
    --field "$pkg" \
    --field "log/$pkg.log.txt" \
    --append \
    --output $task_file \
    -- \
    "${timeout_cmd[@]}" >$log_file 2>&1
  local status=$?
  set -o errexit

  if test "$status" -eq 0; then
    echo "    OK      $(timestamp)  $pkg"
  else
    echo "  FAIL      $(timestamp)  $pkg"
  fi

  # Note: should we try not to fetch here?  I think the caching of "abuilt
  # fetch" might make this OK

  # TODO: avoid running tests and building the APK itself/
  # Only "abuild builddeps,build" is enough to start?
}

"$@"
