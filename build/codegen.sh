#!/usr/bin/env bash
#
# For textual code generation.
#
# Usage:
#   build/codegen.sh <function name>
#
# Examples:
#   build/codegen.sh types-gen
#
# We want a single step build from the git tree, but we also want the generated
# code to be distributed in the release tarball.
#
# For ASDL code generation, re2c, etc.

# NOTE: This is similar to the generation of osh_help.py.

set -o nounset
set -o pipefail
set -o errexit

source build/common.sh

export PYTHONPATH='.:vendor/'

if test -z "${IN_NIX_SHELL:-}"; then
  source build/dev-shell.sh  # to run 're2c'
fi

download-clang() {
  wget --no-clobber --directory _deps \
    http://releases.llvm.org/5.0.1/clang+llvm-5.0.1-x86_64-linux-gnu-ubuntu-16.04.tar.xz
}

extract-clang() {
  cd _deps
  time tar -x --xz < clang*.tar.xz
}

types-gen() {
  local out=_devbuild/gen/osh-types.h
  asdl/tool.py c frontend/types.asdl "$@" > $out
  echo "  (asdl/tool) -> $out"
}

id-c-gen() {
  local out=_devbuild/gen/id.h
  frontend/consts_gen.py c > $out
  echo "  (frontend/consts_gen) -> $out"
}

const-mypy-gen() {
  local out=_devbuild/gen/id_kind_asdl.py
  frontend/consts_gen.py mypy > $out
  log "  (frontend/consts_gen) -> $out"

  out=_devbuild/gen/id_kind.py
  frontend/consts_gen.py py-consts > $out
  log "  (frontend/consts_gen) -> $out"
}

const-cpp-gen() {
  local gc=${1:-}

  local out_dir=_build/cpp

  frontend/consts_gen.py cpp $out_dir/id_kind_asdl
  ls -l $out_dir/id_kind_asdl*

  # TODO: Respect GC=1; Don't use mylib.h
  frontend/consts_gen.py cpp-consts $out_dir/consts${gc}
  ls -l $out_dir/consts*
}

option-mypy-gen() {
  local out=_devbuild/gen/option_asdl.py
  frontend/option_gen.py mypy > $out
  log "  (frontend/option_gen) -> $out"
}

option-cpp-gen() {
  local gc=${1:-}

  # TODO: respect GC=1
  local out_dir=_build/cpp
  frontend/option_gen.py cpp $out_dir/option_asdl${gc}

  # TODO: Respect GC=1; Don't use mylib.h
  core/optview_gen.py > $out_dir/core_optview${gc}.h
  log "  (core/optview_gen) -> $out_dir/core_optview${gc}.h"
}

flag-gen-mypy() {
  local out=_devbuild/gen/arg_types.py
  frontend/flag_gen.py mypy > $out
  #cat $out
  log "  (frontend/flag_gen) -> $out"
}

flag-gen-cpp() {
  local prefix='_build/cpp/arg_types'

  mkdir -p $(dirname $prefix)  # unit tests need this

  frontend/flag_gen.py cpp $prefix
  ls -l $prefix*
}

lexer-gen() { frontend/lexer_gen.py "$@"; }

print-regex() { lexer-gen print-regex; }
print-all() { lexer-gen print-all; }

# re2c native.
osh-lex-gen-native() {
  local in=$1
  local out=$2
  # Turn on all warnings and make them native.
  # The COMMENT state can match an empty string at the end of a line, e.g.
  # '#\n'.  So we have to turn that warning off.
  re2c -W -Wno-match-empty-string -Werror -o $out $in
}

# Called by build/dev.sh for fastlex.so.
ast-id-lex() {
  mkdir -p _devbuild/{gen,tmp}

  #log "-- Generating AST, IDs, and lexer in _devbuild/gen"
  types-gen
  id-c-gen

  local tmp=_devbuild/tmp/osh-lex.re2c.h
  local out=_devbuild/gen/osh-lex.h
  lexer-gen c > $tmp
  echo "  (lexer_gen) -> $tmp"
  osh-lex-gen-native $tmp $out
  echo "$tmp -> (re2c) -> $out"
}

"$@"
