#!/bin/bash
#
# Library shared between test/{spec,spec-alpine,spec-bin}.sh.

SPEC_JOB=${SPEC_JOB:-survey}

readonly BUSYBOX_NAME='busybox-1.31.1'
readonly DASH_NAME='dash-0.5.10.2'
readonly YASH_NAME='yash-2.49'

sh-spec() {
  local test_file=$1
  shift

  if [[ $test_file != *.test.sh ]]; then
    die "Test file should end with .test.sh"
  fi

  local this_dir=$(cd $(dirname $0); pwd)

  local tmp_env=$this_dir/../_tmp/spec-tmp/$(basename $test_file)

  # note: this other _tmp dir is for tests that assume '_tmp' is available
  mkdir -p $tmp_env $tmp_env/_tmp

  # - Prepend spec/bin on the front of the $PATH.  We can't isolate $PATH
  #   because we might be running in Nix, etc.
  # - LOCALE_ARCHIVE is allowed to leak for Nix.
  # - REPO_ROOT is to find things in spec/testdata

  PYTHONPATH=. test/sh_spec.py \
      --tmp-env $tmp_env \
      --path-env "$this_dir/../spec/bin:$PATH" \
      --env-pair "LOCALE_ARCHIVE=${LOCALE_ARCHIVE:-}" \
      --env-pair "REPO_ROOT=$this_dir/.." \
      "$test_file" \
      "$@"
}

