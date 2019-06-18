#!/bin/bash
#
# Install smoosh.  Based on a shell script by Michael Greenberg.  #
#
# Usage:
#   ./smoosh.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly OPAM=~/.opam

# Copies of lem we built inside the repo.
export PATH="$PWD/lem/bin:${PATH}"
export LEMLIB="$PWD/lem/library"


# IMPORTANT: Every function uses this OCaml environment!

eval $(opam config env)


update() {
  #cd ~/git/languages
  #git clone https://github.com/mgree/smoosh
  git pull
  git submodule update --init
}

install-system-deps() {
  # system support for libdash; libgmp for zarith for lem
  sudo apt install autoconf autotools-dev libtool pkg-config libffi-dev libgmp-dev
  # (NOTE: already had all of these.)

  sudo apt install opam
}

opam-switch() {
  # list compilers:
  # opam switch list

  # Version that upstream developers use.  4.02 is the system compiler on
  # Ubuntu 16.04, but that's too old (Sys.int_size not defined)
  opam switch 4.07.0
}

# NOTE: I didn't have opam modify .bashrc.  So from now on it's:
#
# eval $(opam config env)
#
# State is in ~/.opam

install-ocaml-deps() {
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


deps1() {
  # zarith already installed error?

  # Why is this being installed with the system compiler?
  # I have to do "opam switch" as root?

  pushd lem/ocaml-lib 
  opam config exec -- sudo make install_dependencies
  popd
}

build-lem() {
  set -x

  # set up lem
  pushd lem 
  opam config exec -- make
  opam config exec -- make install
  popd
}

build-libdash() {
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
