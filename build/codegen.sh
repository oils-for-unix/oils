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

# Files
#
# native/lex.c -- calls generated function?
# osh/lex.py  -- needs a wrapper for FindLongestMatch?

#
#  ReadToken(lexer_mode, line, s) -> (t, e)

# NOTE: These are in _devbuild because fastlex.so need them, and fastlex.so is
# needed for the Makefile to properly crawl dependencies.
#
# _devbuild/gen/
#    osh-types.h - lex_mode_e for now
#    id_kind.h - id_e for now
#    osh-lex.re2c.c  
#    osh-lex.c  

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
  PYTHONPATH=. osh/ast_gen.py "$@" > _devbuild/gen/osh-types.h
}

id-gen() {
  PYTHONPATH=. core/id_kind_gen.py c > _devbuild/gen/id.h
}

lexer-gen() { PYTHONPATH=. core/lexer_gen.py "$@"; }

# _gen/osh_lex.re2c.c
# This includes osh_ast.h
osh-lex-gen() {
  lexer-gen c > _devbuild/gen/osh-lex.re2c.h
}

print-regex() { lexer-gen print-regex; }
print-all() { lexer-gen print-all; }

# re2c native.
osh-lex-gen-native() {
  # Turn on all warnings and make them native.
  # The COMMENT state can match an empty string at the end of a line, e.g.
  # '#\n'.  So we have to turn that warning off.
  re2c -W -Wno-match-empty-string -Werror \
    -o _devbuild/gen/osh-lex.h _devbuild/gen/osh-lex.re2c.h
}

# Called by build/dev.sh for fastlex.so.
ast-id-lex() {
  mkdir -p _devbuild/gen

  log "-- Generating AST, IDs, and lexer in _devbuild/gen"
  types-gen
  id-gen
  osh-lex-gen
  osh-lex-gen-native
}

# Size profiler for binaries.  TODO: Fold this into benchmarks/
bloaty() { ~/git/other/bloaty/bloaty "$@"; }

stats() {
  local obj=_devbuild/py-ext/x86_64/fastlex.so
  nm $obj
  echo

  bloaty $obj
  echo

  # fastlex_MatchToken is 21.2 KiB.  That doesn't seem to large compared ot
  # the 14K line output?
  bloaty -d symbols $obj
  echo

  ls -l $obj
  echo
}

# NOTES:
# - core/id_kind_gen.py generates the mapping from Id to Kind.
#   - It needs a mapping output by the Python superoptimizatio script.
# - asdl/gen_cpp.py generates oheap code in main().
#   - It should probably be factored into a library and main driver.
#   - Also see asdl/run.sh.

gen-cpp() {
  PYTHONPATH=. asdl/gen_cpp.py cpp osh/osh.asdl
}

"$@"
