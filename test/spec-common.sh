#!/bin/bash
#
# Library shared between test/{spec,spec-alpine}.sh.

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

  PYTHONPATH=. test/sh_spec.py \
      --tmp-env $tmp_env \
      --path-env "$this_dir/../spec/bin:$PATH" \
      --env-pair "LOCALE_ARCHIVE=${LOCALE_ARCHIVE:-}" \
      "$test_file" \
      "$@"
}

