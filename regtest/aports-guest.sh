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

build-package() {
  # Copied from build/deps.sh maybe-install-wedge

  local config=${1:-baseline}
  local pkg=${2:-lua5.4}

  local task_file=$LOG_DIR/$config/$pkg.task.tsv
  local log_file=$LOG_DIR/$config/$pkg.log.txt

  mkdir -p $(dirname $task_file)

  my-time-tsv --print-header \
    --field xargs_slot \
    --field pkg \
    --field pkg_HREF \
    --output $task_file

  # Packages live in /home/udu/aports/main
  # -f forces rebuild: needed for different configs
  local -a cmd=( abuild -f -r -C ~/aports/main/$pkg )

  # Give it 1 second to respond to SIGTERM, then SIGKILL
  local seconds=$(( 5 * 60 ))  # 5 minutes max for now, save time!
  local -a timeout_cmd=( timeout -k 1 $seconds "${cmd[@]}" )

  #set -x
  # NOTE: log/foo.log.txt is the relative path after copy-results; sync-results
  set +o errexit
  my-time-tsv \
    --field "${XARGS_SLOT:-99}" \
    --field "$pkg" \
    --field "log/$pkg.log.txt" \
    --append \
    --output $task_file \
    -- \
    "${timeout_cmd[@]}" >$log_file 2>&1
  local status=$?
  set -o errexit

  if test "$status" -eq 0; then
    echo "    OK  $(timestamp)  $pkg"
  else
    echo "  FAIL  $(timestamp)  $pkg"
  fi

  # Note: should we try not to fetch here?  I think the caching of "abuilt
  # fetch" might make this OK

  # TODO: avoid running tests and building the APK itself/
  # Only "abuild builddeps,build" is enough to start?
}

# leave 1 CPU for other stuff
# Note:
# - Some packages builds use multiple CPUs though ... this is where the GNU
#   make job server protocol would come in handy.
# - We can also compute parallelism LATER from tasks.tsv, with the heuristic
#   USER TIME / ELAPSED  TIME
readonly NPROC=$(( $(nproc) - 1 ))

build-package-list() {
  ### Reads task rows from stdin
  local config=${1:-baseline}
  local parallel=${2:-}

  mkdir -p $LOG_DIR

  local -a flags
  if test -n "$parallel"; then
    log ""
    log "=== Building packages with $NPROC jobs in parallel"
    log ""
    flags=( -P $NPROC )
  else
    log ""
    log "=== Building packages serially"
    log ""
  fi

  # Reads from stdin
  # Note: --process-slot-var requires GNU xargs!  busybox args doesn't have it.
  #
  # $name $version $wedge_dir
  xargs "${flags[@]}" -n 1 --process-slot-var=XARGS_SLOT -- $0 build-package "$config"
}

build-packages() {
  local config=$1  # e.g. baseline
  shift

  for pkg in "$@"; do
    echo "$pkg"
  done | build-package-list "$config"
}


"$@"
