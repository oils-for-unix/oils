#!/bin/bash
#
# Install smoosh.  Based on a shell script by Michael Greenberg.  #
#
# Usage:
#   ./smoosh.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

clone() {
  cd ~/git/languages
  git clone https://github.com/mgree/smoosh
  git submodule update --init
}

install-system-deps() {
  # system support for libdash; libgmp for zarith for lem
  sudo apt install autoconf autotools-dev libtool pkg-config libffi-dev libgmp-dev
  # (NOTE: already had all of these.)

  sudo apt install opam
}

# NOTE: I didn't have opam modify .bashrc.  So from now on it's:
#
# eval $(opam config env)
#
# State is in ~/.opam

install-ocaml-deps() {
  eval $(opam config env)

  # make sure we have ocamlfind and ocamlbuild
  opam install ocamlfind ocamlbuild

  # set up FFI for libdash; num library for lem; extunix for shell syscalls
  opam pin add ctypes 0.11.5
  opam install ctypes-foreign
  opam install num
  opam install extunix
}

link-this-script() {
  local this_script=$PWD/test/smoosh.sh

  ln -s -f -v $this_script ~/git/languages/smoosh
}

readonly OPAM=~/.opam

# Copies of lem we built inside the repo.
export PATH="$PWD/lem/bin:${PATH}"
export LEMLIB="$PWD/lem/library"

_deps1() {
  eval $(opam config env)

  # zarith already installed error?
  pushd lem/ocaml-lib 
  opam config exec -- make install_dependencies
  popd
}

# NOTE: Had to wipe out ~/.opam, do this first, and then do it over?
# Need root to install
deps1() {
  sudo $0 _deps1 "$@"
}

repo-deps() {
  set -x

  eval $(opam config env)

  # set up lem
  pushd lem 
  opam config exec -- make
  opam config exec -- make install
  popd

  # build libdash, expose shared object
  pushd libdash
  ./autogen.sh && ./configure --prefix=/usr --libdir=/usr/lib/x86_64-linux-gnu
  make
  sudo make install
  popd

  # build ocaml bindings
  pushd libdash/ocaml
  opam config exec -- make && opam config exec -- make install
  popd
}

build-smoosh() {
  # build smoosh
  pushd src
  opam config exec -- make all test
  popd
}

"$@"
