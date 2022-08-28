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

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source build/common.sh
source cpp/NINJA-steps.sh  # compile_and_link

export PYTHONPATH='.:vendor/'

if test -z "${IN_NIX_SHELL:-}"; then
  source build/dev-shell.sh  # to run 're2c'
fi

const-mypy-gen() {
  local out=_devbuild/gen/id_kind_asdl.py
  frontend/consts_gen.py mypy > $out
  log "  (frontend/consts_gen) -> $out"

  out=_devbuild/gen/id_kind.py
  frontend/consts_gen.py py-consts > $out
  log "  (frontend/consts_gen) -> $out"
}

option-mypy-gen() {
  local out=_devbuild/gen/option_asdl.py
  frontend/option_gen.py mypy > $out
  log "  (frontend/option_gen) -> $out"
}

flag-gen-mypy() {
  local out=_devbuild/gen/arg_types.py
  frontend/flag_gen.py mypy > $out
  #cat $out
  log "  (frontend/flag_gen) -> $out"
}

test-optview() {
  ninja _build/cpp/core_optview.h _build/cpp/option_asdl.h

  local tmp_dir=_test/gen-cpp/core
  local bin_dir=_bin/cxx-asan/core
  mkdir -p $tmp_dir $bin_dir

  cat >$tmp_dir/optview_test.cc <<'EOF'
#include "_build/cpp/core_optview.h"

int main() {
  printf("OK optview_test\n");
  return 0;
}
EOF

  local bin=$bin_dir/optview_test

  compile_and_link cxx asan '' $bin \
    $tmp_dir/optview_test.cc

  log "RUN $bin"
  $bin
}

test-flag-gen() {
  ninja _build/cpp/arg_types.{h,cc}

  local tmp_dir=_test/gen-cpp/core
  local bin_dir=_bin/cxx-asan/core
  mkdir -p $tmp_dir $bin_dir

  cat >$tmp_dir/arg_types_test.cc <<'EOF'
#include "_build/cpp/arg_types.h"

int main() {
  printf("kFlagSpecs %p\n", arg_types::kFlagSpecs);
  printf("OK arg_types_test\n");
  return 0;
}
EOF

  local bin=$bin_dir/arg_types_test

  compile_and_link cxx asan '' $bin \
    _build/cpp/arg_types.cc \
    $tmp_dir/arg_types_test.cc

  log "RUN $bin"
  $bin
}

lexer-gen() { frontend/lexer_gen.py "$@"; }

print-regex() { lexer-gen print-regex; }
print-all() { lexer-gen print-all; }

types-gen() {
  local out=_devbuild/gen/osh-types.h
  asdl/asdl_main.py c frontend/types.asdl "$@" > $out
  log "  (asdl_main c) -> $out"
}

id-c-gen() {
  local out=_devbuild/gen/id.h
  frontend/consts_gen.py c > $out
  log "  (frontend/consts_gen c) -> $out"
}

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
  log "  (lexer_gen) -> $tmp"
  osh-lex-gen-native $tmp $out
  log "$tmp -> (re2c) -> $out"
}

test-generated-code() {
  test-optview
  echo

  test-flag-gen
  echo
}

"$@"
