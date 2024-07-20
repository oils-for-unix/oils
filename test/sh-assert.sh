# test/sh-assert.sh

section-banner() {
  echo
  echo '///'
  echo "/// $1"
  echo '///'
  echo
}

case-banner() {
  echo
  echo ===== CASE: "$@" =====
  echo
}

_assert-sh-status() {
  ### The most general assertion - EXIT on failure

  local expected_status=$1
  local sh=$2
  local message=$3
  shift 3

  case-banner "$@"
  echo

  set +o errexit
  $sh "$@"
  local status=$?
  set -o errexit

  if test -z "${SH_ASSERT_DISABLE:-}"; then
    if test "$status" != "$expected_status"; then
      echo
      die "$message: expected status $expected_status, got $status"
    fi
  fi
}

#
# Assertions using _assert-sh-status
#

_osh-error-X() {
  local expected_status=$1
  shift

  local message="Should FAIL under $OSH"
  _assert-sh-status "$expected_status" "$OSH" "$message" \
    -c "$@"
}

_osh-error-here-X() {
  _osh-error-X $1 "$(cat)"
}


_osh-error-1() {
  _osh-error-X 1 "$@"
}

_osh-error-2() {
  _osh-error-X 2 "$@"
}

_ysh-error-X() {
  local expected_status=$1
  shift

  local message=$0
  _assert-sh-status $expected_status $YSH "$message" \
    -c "$@"
}

_ysh-error-here-X() {
  _ysh-error-X $1 "$(cat)"
}

_ysh-error-1() {
  ### Expect status 1
  _ysh-error-X 1 "$@"
}

_ysh-error-2() {
  ### Expect status 2
  _ysh-error-X 2 "$@"
}

_ysh-expr-error() {
  ### Expect status 3
  _ysh-error-X 3 "$@"
}

_osh-should-run() {
  local message="Should run under $OSH"
  _assert-sh-status 0 $OSH "$message" \
    -c "$@"
}

_ysh-should-run() {
  local message="Should run under $YSH"
  _assert-sh-status 0 $YSH "$message" \
    -c "$@"
}

#
# Parse errors - pass -n -c, instead of -c
#

_osh-should-parse() {
  local message="Should parse with $OSH"
  _assert-sh-status 0 $OSH "$message" \
    -n -c "$@"
}

_osh-parse-error() {
  ### Pass a string that should NOT parse as $1
  local message="Should NOT parse with $OSH"
  _assert-sh-status 2 $OSH "$message" \
    -n -c "$@"
}

_ysh-should-parse() {
  local message="Should parse with $YSH"
  _assert-sh-status 0 $YSH "$message" \
    -n -c "$@"
}

_ysh-parse-error() {
  local message="Should NOT parse with $YSH"
  _assert-sh-status 2 $YSH "$message" \
    -n -c "$@"
}

#
# Here doc variants, so we can write single quoted strings in a
# more readable way
#

_osh-should-parse-here() {
  _osh-should-parse "$(cat)"
}

_osh-parse-error-here() {
  _osh-parse-error "$(cat)"
}

_ysh-should-parse-here() {
  _ysh-should-parse "$(cat)"
}

_ysh-parse-error-here() {
  _ysh-parse-error "$(cat)"
}

_osh-should-run-here() {
  _osh-should-run "$(cat)"
}

_ysh-should-run-here() {
  _ysh-should-run "$(cat)"
}

