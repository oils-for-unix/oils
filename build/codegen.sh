#!/bin/bash
#
# For textual code generation.
#
# Usage:
#   ./codegen.sh <function name>
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

# Files
#
# native/lex.c -- calls generated function?
# osh/lex.py  -- needs a wrapper for FindLongestMatch?

#
#  ReadToken(lexer_mode, line, s) -> (t, e)

# NOTE: These are in _devbuild because fastlex.so need them, and fastlex.so is
# needed for the Makefile to properly crawl dependencies.
#
# _devbuild/
#   gen/
#     osh-types.h - lex_mode_e
#     id_kind.h - Id
#     osh-lex.h
#   tmp/
#    osh-lex.re2c.c

download-re2c() {
  mkdir -p _deps
  wget --directory _deps \
    https://github.com/skvadrik/re2c/releases/download/1.0.3/re2c-1.0.3.tar.gz
}

install-re2c() {
  cd _deps
  tar -x -z < re2c-1.0.3.tar.gz
  cd re2c-1.0.3
  ./configure
  make
}

re2c() { _deps/re2c-1.0.3/re2c "$@"; }

download-clang() {
  wget --directory _deps \
    http://releases.llvm.org/5.0.1/clang+llvm-5.0.1-x86_64-linux-gnu-ubuntu-16.04.tar.xz
}

extract-clang() {
  cd _deps
  time tar -x --xz < clang*.tar.xz
}

types-gen() {
  asdl/tool.py c frontend/types.asdl "$@" > _devbuild/gen/osh-types.h
}

id-c-gen() {
  frontend/id_kind_gen.py c > _devbuild/gen/id.h
}

id-mypy-gen() {
  local out=_devbuild/gen/id_kind_asdl.py
  frontend/id_kind_gen.py mypy > $out
  log "Wrote $out"

  out=_devbuild/gen/id_tables.py
  frontend/id_kind_gen.py py-tables > $out
  log "Wrote $out"
}

id-cpp-gen() {
  local out_dir=_build/cpp
  frontend/id_kind_gen.py cpp $out_dir/id_kind_asdl

  frontend/id_kind_gen.py cc-tables $out_dir/lookup
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

  log "-- Generating AST, IDs, and lexer in _devbuild/gen"
  types-gen
  id-c-gen

  local tmp=_devbuild/tmp/osh-lex.re2c.h
  lexer-gen c > $tmp
  osh-lex-gen-native $tmp _devbuild/gen/osh-lex.h
}

# NOTES:
# - frontend/id_kind_gen.py generates the mapping from Id to Kind.
#   - It needs a mapping output by the Python superoptimizatio script.
# - asdl/gen_cpp.py generates oheap code in main().
#   - It should probably be factored into a library and main driver.
#   - Also see asdl/run.sh.

gen-cpp() {
  asdl/gen_cpp.py cpp osh/osh.asdl
}

"$@"
