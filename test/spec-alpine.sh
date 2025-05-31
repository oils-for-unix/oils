#!/usr/bin/env bash
#
# Analogous to test/spec.sh, but for the environment set up by test/alpine.sh.
#
# Usage:
#   test/spec-alpine.sh <function name>

set -o nounset
set -o pipefail
set -o errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

source test/common.sh
source test/spec-common.sh

readonly SH=osh  # just use the one in the $PATH

builtin-bracket() {
  # some tests depend on 'bin' existing
  # Also running as root so you can read anything!  Doh!  Need a real user.
  sh-spec spec/builtin-bracket.test.sh --oils-failures-allowed 3 \
    $SH "$@"
}

# This is bash/OSH only
builtin-completion() {
  # 8 failures instead of 1
  sh-spec spec/builtin-completion.test.sh --oils-failures-allowed 8 \
    $SH "$@"
}

builtin-eval-source() {
  sh-spec spec/builtin-eval-source.test.sh $SH "$@"
}

builtin-trap() {
  sh-spec spec/builtin-trap.test.sh --oils-failures-allowed 3 \
    $SH "$@"
}

builtins() {
  # 6 failures instead of 1
  sh-spec spec/builtins.test.sh --oils-failures-allowed 6 \
    $SH "$@"
}

errexit-oil() {
  sh-spec spec/errexit-oil.test.sh $SH "$@"
}

glob() {
  # 11 failures rather than 7 under Ubuntu.  Probably due to musl libc globbing
  # differences.
  sh-spec spec/glob.test.sh --oils-failures-allowed 11 \
    $SH "$@"
}

introspect() {
  sh-spec spec/introspect.test.sh $SH "$@"
}

loop() {
  # 1 failure instead of 0
  sh-spec spec/loop.test.sh --oils-failures-allowed 1 \
    $SH "$@"
}

smoke() {
  # 1 failure instead of 0
  sh-spec spec/smoke.test.sh --oils-failures-allowed 1 $SH "$@"
}

strict-options() {
  sh-spec spec/strict-options.test.sh $SH "$@"
}

var-op-len() {
  sh-spec spec/var-op-len.test.sh $SH "$@"
}

run-file() {
  ### Run a test with the given name.

  local test_name=$1
  shift

  if declare -F "$test_name"; then
    # Delegate to a function in this file.
    "$test_name" "$@"
  else
    # Run it with OSH
    sh-spec spec/$test_name.test.sh $SH "$@"
  fi
}

all() {
  # TODO: Test this function and run in CI

  export OSH_LIST=osh YSH_LIST=ysh

  # this is like test/spec.sh {oil,osh}-all
  # $suite $compare_mode $spec_subdir
  test/spec-runner.sh all-parallel oil release-alpine oil-language
  test/spec-runner.sh all-parallel osh release-alpine survey
}

home-page() {
  cat <<EOF
<h1>Spec Test Results</h2>

<a href="_tmp/spec/osh.html">osh.html</a> <br/>
<a href="_tmp/spec/oil.html">oil.html</a> <br/>

EOF
}

# oilshell.org/spec-results/$date-$hostname-$distro.wwz/
#   _tmp/spec/     # from _tmp/spec
#     osh.html
#     oil.html
#   web/           # from web

manifest() {
  find index.html _tmp/spec/ web/ -type f 
}

archive-results() {
  local archive_type=${1:-zip}  # zip or tar

  home-page > index.html
  local out_name="$(date +%Y-%m-%d__%H-%M-%S)__$(hostname)"

  case $archive_type in
    # zip isn't in POSIX so some systems might not have it.
    tar)
      local out=$out_name.tar.gz
      manifest | xargs -- tar -c -z > $out
      ;;

    zip)
      # .wwz is just a zip file that is served
      local out=$out_name.wwz
      manifest | xargs -- zip $out
      ;;

    *)
      die "Invalid type $archive_type"
      ;;
  esac

  ls -l $out
}

"$@"
