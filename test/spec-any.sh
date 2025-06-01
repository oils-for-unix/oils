#!/usr/bin/env bash
#
# Test OSH against any shell
#
# Usage:
#   test/spec-any.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source test/common.sh
source test/spec-common.sh

OSH=_bin/cxx-asan/osh
ninja $OSH
OSH=$PWD/$OSH

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

readonly BRUSH_DIR=~/install/brush

# Note: we have the repo too
download-brush-binary() {
  # The musl libc build works on my old Ubuntu VM, because it's statically linked
  # The GNU one doesn't work
  wget --directory $BRUSH_DIR --no-clobber \
    https://github.com/reubeno/brush/releases/download/brush-shell-v0.2.18/brush-x86_64-unknown-linux-musl.tar.gz
    #https://github.com/reubeno/brush/releases/download/brush-shell-v0.2.18/brush-x86_64-unknown-linux-gnu.tar.gz
}

#BRUSH=$BRUSH_DIR/brush

readonly TOYBOX_DIR=~/src/toybox-0.8.12

readonly SUSH_DIR=../../shells/rusty_bash

# these are all roughly ksh compatible
readonly -a SHELLS=(bash mksh ksh $TOYBOX_DIR/sh $PWD/$SUSH_DIR/target/release/sush $OSH)

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
  pushd ../../shells/brush

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
  pushd ../../shells/rusty_bash

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
  # stripped: 2.4 MB
  ls -l --si $oils

  pushd ../../shells/brush
  strip -o target/release/brush.stripped target/release/brush
  # stripped: 7.1 MB
  ls -l --si target/release
  popd

  pushd ../../shells/rusty_bash
  strip -o target/release/sush.stripped target/release/sush
  # stripped: 3.9 MB
  ls -l --si target/release
  echo
  popd
}

symbols() {
  pushd ../../shells/brush
  #file target/release/brush

  echo 'BRUSH'
  # 6140
  nm target/release/brush | wc -l
  popd

  pushd ../../shells/rusty_bash
  # Not stripped
  #file target/release/sush

  echo 'SUSH'
  # 10380
  nm target/release/sush | wc -l
  # More symbols
  # nm target/debug/sush | wc -l
  popd

  #local osh=_bin/cxx-opt/bin/oils_for_unix.mycpp.stripped
  local osh=_bin/cxx-opt/bin/oils_for_unix.mycpp
  local dbg=_bin/cxx-dbg/bin/oils_for_unix.mycpp
  ninja $osh 

  echo 'OSH'
  # 9810 - lots of string literals?
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
  local spec_name=$1
  shift  # Pass list of shells
  
  # spec/tilde hangs under toysh - need timeout
  sh-spec spec/$spec_name.test.sh \
    --timeout 1 \
    "$@"
}

compare() {
  local spec_name=${1:-smoke}
  run-file $spec_name "${SHELLS[@]}"
}

list() {
  mkdir -p _tmp/spec  # _all-parallel also does this
  test/spec-runner.sh write-suite-manifests
  wc -l _tmp/spec/SUITE-*

  # TODO:
  # - Remove zsh test files?
  # - What about *-bash test cases?  These aren't clearly organized

  cat _tmp/spec/SUITE-osh.txt
}

task-five "$@"
