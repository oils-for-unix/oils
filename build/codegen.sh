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

# Files
#
# native/lex.c -- calls generated function?
# osh/lex.py  -- needs a wrapper for FindLongestMatch?

#
#  ReadToken(lexer_mode, line, s) -> (t, e)

# _build/gen/
#    osh-ast.h - lex_mode_e for now
#    id_kind.h - id_e for now
#    osh-lex.re2c.c  
#    osh-lex.c  

re2c() {
  ~/src/re2c-0.16/re2c "$@"
}

ast-gen() {
  PYTHONPATH=. osh/ast_gen.py "$@" | tee _build/gen/osh-ast.h
}

id-gen() {
  PYTHONPATH=. core/id_kind_gen.py c | tee _build/gen/id.h
}

# _gen/osh_lex.re2c.c
# This includes osh_ast.h
lex-gen() {
  PYTHONPATH=. osh/lex_gen.py "$@" | tee _build/gen/osh-lex.re2c.h
}

# re2c native.
lex-gen-native() {
  re2c -o _build/gen/osh-lex.h _build/gen/osh-lex.re2c.h
}

all() {
  ast-gen
  id-gen
  lex-gen
  lex-gen-native

  # Why do we need this?
  rm -f _devbuild/pylibc/x86_64/lex.so

  # Note: This also does pylibc, which we don't want.
  build/dev.sh all
}

symbols() {
  nm _devbuild/pylibc/x86_64/lex.so
}

# Then the next step is build/dev.sh pylibc?


# NOTES:
# - core/id_kind_gen.py generates the mapping from Id to Kind.
#   - It needs a mapping output by the Python superoptimizatio script.
# - asdl/gen_cpp.py generates oheap code in main().
#   - It should probably be factored into a library and main driver.

# This generates oheap code.
# Also see asdl/run.sh.

gen-cpp() {
  PYTHONPATH=. asdl/gen_cpp.py cpp osh/osh.asdl
}

"$@"
