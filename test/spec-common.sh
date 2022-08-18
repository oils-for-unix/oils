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

  local tmp_env
  tmp_env=$this_dir/../_tmp/spec-tmp/$(basename $test_file)

  # note: this other _tmp dir is for tests that assume '_tmp' is available
  mkdir -p $tmp_env $tmp_env/_tmp

  # - Prepend spec/bin on the front of the $PATH.  We can't isolate $PATH
  #   because we might be running in Nix, etc.
  # - Force LC_ALL=C.UTF-8 because
  #   - bash behaves differently with en_US.UTF-8, but no other shell does.
  #     (Not sure if OSH should support it, probably not.)
  #   - en_US.UTF-8 seems hard to support on Debian, even though it's the default on Debian.
  #   - Description: https://stackoverflow.com/questions/55673886/what-is-the-difference-between-c-utf-8-and-en-us-utf-8-locales/55693338
  # - LOCALE_ARCHIVE is allowed to leak for Nix.
  # - ASAN_OPTIONS leaks for memory
  # - REPO_ROOT is to find things in spec/testdata

  PYTHONPATH=. test/sh_spec.py \
      --tmp-env $tmp_env \
      --path-env "$this_dir/../spec/bin:$PATH" \
      --env-pair 'LC_ALL=C.UTF-8' \
      --env-pair "LOCALE_ARCHIVE=${LOCALE_ARCHIVE:-}" \
      --env-pair "ASAN_OPTIONS=${ASAN_OPTIONS:-}" \
      --env-pair "REPO_ROOT=$this_dir/.." \
      "$test_file" \
      "$@"
}

