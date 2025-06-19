#!/usr/bin/env bash
#
# Test OSH against any shell
#
# Usage:
#   test/spec-compat.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source build/dev-shell.sh  # put mksh etc. in $PATH
source test/common.sh
source test/spec-common.sh

OSH_TARGET=_bin/cxx-asan/osh
OSH=$PWD/$OSH_TARGET

# To compare against:
# - toysh
# - brush
# - rusty_bash
# - ksh93 - Debian package

# Metrics
# - binary size - stripped
# - lines of source code - I think we get this from DWARF debug info
#   - https://claude.ai/chat/40597e2e-4d1e-42b4-a756-7a265f01cc5a shows options
#   - llvm-dwarfdump
#   - Python lib https://github.com/eliben/pyelftools/
#   - right now this isn't worth it - spec tests are more important
# - unsafe functions / methods?
#   - cargo geiger is also hard to parse

readonly TOYBOX_DIR=~/src/toybox-0.8.12

readonly SUSH_DIR=../../shells/rusty_bash
readonly BRUSH_DIR=../../shells/brush

readonly SUSH=$PWD/$SUSH_DIR/target/release/sush 
readonly BRUSH=$PWD/$BRUSH_DIR/target/release/brush

# these are all roughly ksh compatible
readonly -a SHELLS=(bash dash ash zsh mksh ksh $TOYBOX_DIR/sh $SUSH $BRUSH $OSH)

download-toybox() {
  #mkdir -p ~/src
  wget --directory ~/src --no-clobber \
    https://landley.net/toybox/downloads/toybox-0.8.12.tar.gz
}

build-toybox() {
  pushd $TOYBOX_DIR

  make toybox
  # warning: using unfinished code
  make sh

  popd
}

update-rust() {
  . ~/.cargo/env
  time rustup update
}

build-brush() {
  local pull=${1:-}

  pushd ../../shells/brush

  if test -n "$pull"; then
    git pull
  fi

  . ~/.cargo/env

  # Test incremental build speed
  # - debug: 3.8 seconds
  # - release: 1:06 minutes !
  # touch brush-core/src/shell.rs

  # 41s
  time cargo build
  echo

  # 1m 49s
  # It builds a stripped binary by default - disable that for metrics
  RUSTFLAGS='-C strip=none' time cargo build --release
  echo

  popd
}

build-sush() {
  local pull=${1:-}

  pushd ../../shells/rusty_bash

  if test -n "$pull"; then
    git pull
  fi

  . ~/.cargo/env

  # Test incremental build speed
  # - debug: 1 second
  # - release: 6 seconds
  #touch src/core.rs

  # 10 seconds
  time cargo build
  echo

  # 15 seconds
  time cargo build --release
  echo

  popd
}

binary-sizes() {
  local oils=_bin/cxx-opt/bin/oils_for_unix.mycpp.stripped
  ninja $oils

  pushd $BRUSH_DIR
  local out=target/release/brush.stripped 
  strip -o $out target/release/brush
  local brush=$BRUSH_DIR/$out
  popd

  pushd $SUSH_DIR
  local out=target/release/sush.stripped 
  strip -o $out target/release/sush
  local sush=$SUSH_DIR/$out
  popd

  echo
  ls -l --si $oils $brush $sush $TOYBOX_DIR/sh

  # These aren't dynamically linked to GNU readline, or libstdc++
  echo
  ldd $oils $brush $sush $TOYBOX_DIR/sh
}

symbols() {
  pushd ../../shells/brush
  #file target/release/brush

  echo 'BRUSH'
  # 6272
  nm target/release/brush | wc -l
  popd

  pushd ../../shells/rusty_bash
  # Not stripped
  #file target/release/sush

  echo 'SUSH'
  # 4413
  nm target/release/sush | wc -l
  # More symbols
  # nm target/debug/sush | wc -l
  popd

  #local osh=_bin/cxx-opt/bin/oils_for_unix.mycpp.stripped
  local osh=_bin/cxx-opt/bin/oils_for_unix.mycpp
  local dbg=_bin/cxx-dbg/bin/oils_for_unix.mycpp
  ninja $osh 

  echo 'OSH'
  # 9857 - lots of string literals?
  nm $osh | wc -l
  #nm $osh | less

  #ninja $dbg
  # 17570
  #nm $dbg | wc -l
}

install-geiger() {
  # https://github.com/geiger-rs/cargo-geiger
  . ~/.cargo/env

  # 2:34 minutes
  cargo install --locked cargo-geiger
}

# This is DESTRUCTIVE
geiger-report() {
  if true; then
    pushd ../../shells/brush

    . ~/.cargo/env

    # doesn't work
    #time cargo geiger --workspace
    #time cargo geiger --package brush-core --package brush-parser

    popd
  fi

  if false; then
    pushd ../../shells/rusty_bash

    . ~/.cargo/env

    # this cleans the build
    #
    # Functions  Expressions  Impls   Traits  Methods
    # 181/1056   9377/45040   114/158 30/32   463/2887
    #
    # x/y
    # x = unsafe used by build
    # y = unsafe in crate

    # ~7 seconds
    time cargo geiger 

    popd
  fi
}

#
# Spec Tests
#

run-file() {
  local spec_name=${1:-smoke}
  shift  # Pass list of shells

  local spec_subdir='compat'
  local base_dir=_tmp/spec/$spec_subdir
  mkdir -v -p $base_dir
  
  # spec/tilde hangs under toysh - need timeout
  sh-spec spec/$spec_name.test.sh \
    --tsv-output $base_dir/${spec_name}.result.tsv \
    --timeout 1 \
    "$@" \
    "${SHELLS[@]}"
}

osh-all() {
  # Since we're publishing these, make sure we start with a clean slate
  rm -r -f -v _tmp/spec

  ninja $OSH_TARGET

  test/spec-runner.sh shell-sanity-check "${SHELLS[@]}"

  local spec_subdir=compat

  local status
  set +o errexit
  # $suite $compare_mode
  test/spec-runner.sh all-parallel \
    compat spec-compat $spec_subdir "$@"
  status=$?
  set -o errexit

  # Write comparison even if we failed
  test/spec-compat-html.sh write-compare-html $spec_subdir

  return $status
}

#
# Misc
#

list() {
  mkdir -p _tmp/spec  # _all-parallel also does this
  test/spec-runner.sh write-suite-manifests
  wc -l _tmp/spec/SUITE-*

  # TODO:
  # - Remove zsh test files?
  # - What about *-bash test cases?  These aren't clearly organized

  cat _tmp/spec/SUITE-osh.txt
}

readonly ERRORS=(
  'echo )'  # parse error
  'cd -z'   # usage error
  'cd /zzz'   # runtime error
)

survey-errors() {
  set +o errexit
  for sh in "${SHELLS[@]}"; do
    echo
    echo " === $sh"
    for code in "${ERRORS[@]}"; do
      $sh -c "$code"
    done
  done
}

task-five "$@"
