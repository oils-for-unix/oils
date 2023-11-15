#!/usr/bin/env bash
#
# Library shared between test/{spec,spec-alpine,spec-bin}.sh.

readonly BASH_NAME='bash-4.4'  # TODO: 5.1 upgrade
readonly BUSYBOX_NAME='busybox-1.35.0'
readonly DASH_NAME='dash-0.5.10.2'
readonly YASH_NAME='yash-2.49'

sh-spec() {
  local test_file=$1
  shift

  if [[ $test_file != *.test.sh ]]; then
    die "Test file should end with .test.sh"
  fi

  local this_dir
  this_dir=$(cd $(dirname $0); pwd)

  # Create under PID dir
  local tmp_env
  tmp_env=$this_dir/../_tmp/spec-tmp/$$/$(basename $test_file)

  # In the rare case that the PID dir exists, blow it away
  if test -d $tmp_env; then
    rm -r -f $tmp_env
  fi
  # In general we leave the tmp dir around so you can inspect it.  It's always
  # safe to get rid of the cruft like this:
  #
  # rm -r -f _tmp/spec-tmp

  # - Prepend spec/bin on the front of the $PATH.  We can't isolate $PATH
  #   because we might be running in Nix, etc.
  # - Force LC_ALL=C.UTF-8 because
  #   - bash behaves differently with en_US.UTF-8, but no other shell does.
  #     (Not sure if OSH should support it, probably not.)
  #   - en_US.UTF-8 seems hard to support on Debian, even though it's the default on Debian.
  #   - Description: https://stackoverflow.com/questions/55673886/what-is-the-difference-between-c-utf-8-and-en-us-utf-8-locales/55693338
  # - LOCALE_ARCHIVE is allowed to leak for Nix.
  # - OILS_GC_ON_EXIT is to pass ASAN.
  # - REPO_ROOT is to find things in spec/testdata

  PYTHONPATH=. test/sh_spec.py \
      --tmp-env "$tmp_env" \
      --path-env "$this_dir/../spec/bin:$PATH" \
      --env-pair 'LC_ALL=C.UTF-8' \
      --env-pair "LOCALE_ARCHIVE=${LOCALE_ARCHIVE:-}" \
      --env-pair "OILS_GC_ON_EXIT=${OILS_GC_ON_EXIT:-}" \
      --env-pair "REPO_ROOT=$this_dir/.." \
      "$test_file" \
      "$@"

  # Don't need this now that we have OILS_GC_ON_EXIT
  #    --env-pair "ASAN_OPTIONS=${ASAN_OPTIONS:-}" \
}

# Usage: callers can override OSH_LIST to test on more than one version.
#
# Example:
# OSH_LIST='bin/osh _bin/osh' test/spec-py.sh osh-all

readonly OSH_CPYTHON="$REPO_ROOT/bin/osh"
readonly OSH_OVM=${OSH_OVM:-$REPO_ROOT/_bin/osh}

OSH_LIST=${OSH_LIST:-}  # A space-separated list.

if test -z "$OSH_LIST"; then
  # By default, run with both, unless $OSH_OVM isn't available.
  if test -e $OSH_OVM; then
    # TODO: Does it make sense to copy the binary to an unrelated to directory,
    # like /tmp?  /tmp/{oil.ovm,osh}.
    OSH_LIST="$OSH_CPYTHON $OSH_OVM"
  else
    OSH_LIST="$OSH_CPYTHON"
  fi
fi

readonly YSH_CPYTHON="$REPO_ROOT/bin/ysh"
readonly YSH_OVM=${YSH_OVM:-$REPO_ROOT/_bin/ysh}

YSH_LIST=${YSH_LIST:-}  # A space-separated list.

if test -z "$YSH_LIST"; then
  # By default, run with both, unless $YSH_OVM isn't available.
  if test -e $YSH_OVM; then
    YSH_LIST="$YSH_CPYTHON $YSH_OVM"
  else
    YSH_LIST="$YSH_CPYTHON"
  fi
fi

