# Usage:
#   source test/common.sh

# Include guard.
test -n "${__TEST_COMMON_SH:-}" && return
readonly __TEST_COMMON_SH=1

# Used by test/{gold,osh-usage,stateful,wild-runner}
OSH=${OSH:-'bin/osh'}

# For xargs -P in spec-runner.sh, wild-runner.sh.
# If we have 2 cores or less (as on CI machines), use them all.  Otherwise save
# 1 for multitasking.
nproc=$(nproc)
MAX_PROCS=${MAX_PROCS:-"$(( nproc <= 2 ? nproc : nproc - 1 ))"}

# Like PYTHONPATH, but for running R scripts
# Fallback in build/dev-shell.sh
readonly R_PATH=~/R

log() {
  echo "$@" 1>&2
}

die() {
  log "$@"
  exit 1
}

fail() {
  echo 'TEST FAILURE  ' "$@"
  exit 1
}

assert() {
  ### Must be run with errexit off

  if ! test "$@"; then
    # note: it's extremely weird that we use -1 and 0, but that seems to be how
    # bash works.
    die "${BASH_SOURCE[-1]}:${BASH_LINENO[0]}: assert '$@' failed"
  fi
}

run-task-with-status() {
  ### Run a process and write a file with status and time

  # Used by test/{spec,wild}-runner.sh

  local out_file=$1
  shift

  benchmarks/time_.py \
    --tsv \
    --output $out_file \
    -- "$@" || true  # suppress failure

  # TODO: Use rows like this in YSH
  # '{"status": %x, "wall_secs": %e, "user_secs": %U, "kernel_secs": %S}' \
}

list-test-funcs() {
  ### Shell funcs that start with 'test-' are cases that will pass or fail
  compgen -A function | egrep '^test-' 
}

run-test-funcs() {
  # for correct error handling, and to mutate $i
  #
  # Note: when I ran $t rather than $0 t, I seemed to tickle a bash lastpipe bug like this:
  # https://www.spinics.net/lists/dash/msg01918.html
  # I got a 127 exit code with no explanation.
  shopt -s lastpipe

  local i=0
  local status=0

  list-test-funcs | while read t; do
    echo "*** Running $t"

    set +o errexit
    $0 $t
    status=$?
    set -o errexit

    if test $status -ne 0; then
      log "FAIL  $t"
      exit 1
    fi

    log "OK  $t"
    i=$((i + 1))
  done

  echo
  echo "$0: $i tests passed."
}

run-test-bin() {
  ### Run a binary in _bin/ and log output to a file in _test/

  # Compare with run-test-funcs
  local bin=$1
  local working_dir=${2:-}
  local log_base_dir=${3:-'_test'}  # used by test/unit.sh

  local rel_path=${bin#'_bin/'}  # for C++ only
  local log_dir="$log_base_dir/$(dirname $rel_path)"
  mkdir -p $REPO_ROOT/$log_dir  # abs path

  local name=$(basename $bin)
  export LLVM_PROFILE_FILE="$REPO_ROOT/$log_dir/$name.profraw"

  local log=$log_dir/$name.log
  log "RUN $bin > $log"

  if test -n "$working_dir"; then
    pushd $working_dir
  fi

  set +o errexit
  $REPO_ROOT/$bin > $REPO_ROOT/$log 2>&1
  local status=$?
  set -o errexit

  if test -n "$working_dir"; then
    popd
  fi

  if test $status -eq 0; then
    log 'OK'
  else
    echo
    echo "=== $REPO_ROOT/$log ==="
    echo
    cat $REPO_ROOT/$log
    echo
    log "FAIL: $bin with code $status"
    return 1
  fi
}

run-one-test() {
  local rel_path=$1
  local compiler=${2:-cxx}
  local variant=${3:-dbg}

  local bin=_bin/$compiler-$variant/$rel_path

  ninja $bin

  run-test-bin $bin
}

run-test-func() {
  ### Similar to above
  local func_name=$1
  local log=$2
  shift 2

  mkdir -p $(dirname $log)
  log "RUN $0 $func_name > $log"

  set +o errexit

  # Reinvoke $0 so errexit is on in the function
  $0 $func_name "$@" > $log 2>&1
  local status=$?

  set -o errexit

  if test $status -eq 0; then
    log 'OK'
  else
    echo
    cat $log
    echo
    log "FAIL: $func_name with code $status"
    return 1
  fi
}

# A quick and dirty function to show logs
run-other-suite-for-release() {
  local suite_name=$1
  local func_name=$2

  local out="_tmp/suite-logs/${suite_name}.txt"
  mkdir -p $(dirname $out)

  echo
  echo "*** Running test suite '$suite_name' ***"
  echo

  # I want to handle errors in $func_name while NOT changing its semantics.
  # This requires a separate shell interpreter starts with $0, not just a
  # separate process.  I came up with this fix in gold/errexit-confusion.sh.

  local status=0

  set +o errexit
  time $0 $func_name >$out 2>&1
  status=$?  # pipefail makes this work.
  set -o errexit

  if test $status -eq 0; then
    echo
    log "Test suite '$suite_name' ran without errors.  Wrote '$out'"
  else
    echo
    die "Test suite '$suite_name' failed (running $func_name, wrote '$out')"
  fi
}

date-and-git-info() {
  date
  echo

  if test -d .git; then
    local branch
    branch=$(git rev-parse --abbrev-ref HEAD)
    local hash
    hash=$(git rev-parse $branch)

    echo "oil repo: $hash on branch $branch"
  else
    echo "(not running from git repository)"
  fi
  echo
}

html-head() {
  PYTHONPATH=. doctools/html_head.py "$@"
}

escape-html() {
  # Annoying that & has to be escaped in substitution!
  sed -e 's|&|\&amp;|g' -e 's|<|\&lt;|g' -e 's|>|\&gt;|g' "$@"
}

export-osh-cpp() {
  ### Export $OSH var to value in tarball root, repo root

  # Also build it with shell script, or Ninja

  local tar_root=${1:-}  # e.g. _tmp/native-tar-test
  local variant=${2:-opt}

  if test -n "$tar_root" && test -d "$tar_root"; then
    log "Using binary in $tar_root"

    OIL_VERSION=$(head -n 1 oil-version.txt)
    local repo_like=$tar_root/oils-for-unix-$OIL_VERSION

    pushd $repo_like
    _build/oils.sh '' $variant SKIP_REBUILD
    osh=$PWD/_bin/cxx-$variant-sh/osh
    popd

  else
    osh=_bin/cxx-$variant/osh
    ninja $osh
  fi

  # So we can find it
  export OSH=$osh
  log "Exported OSH=$OSH"
}

