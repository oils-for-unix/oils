# test/sh-assert.sh

banner() {
  echo
  echo ===== CASE: "$@" =====
  echo
}

_assert-sh-status() {
  ### The most general assertion

  local expected_status=$1
  local sh=$2
  local message=$3
  shift 3

  banner "$@"
  echo
  $sh "$@"
  local status=$?
  if test $status != $expected_status; then
    die "$message: expected status $expected_status, got $status"
  fi
}
