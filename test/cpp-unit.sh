#!/usr/bin/env bash
#
# Run C++ unit tests.
#
# Usage:
#   test/cpp-unit.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

soil-run() {
  ./NINJA_config.py

  # uses Ninja to run (cxx, testgc) variant.  Could also run (clang, ubsan),
  # which finds more bugs.
  mycpp/test.sh soil-run

  # This is part of build/dev.sh oil-cpp
  build/codegen.sh ast-id-lex  # id.h, osh-types.h, osh-lex.h
  build/codegen.sh flag-gen-cpp  # _build/cpp/arg_types.h
  build/dev.sh oil-asdl-to-cpp  # unit tests depend on id_kind_asdl.h, etc.
  build/dev.sh cpp-codegen

  cpp/test.sh unit

  asdl/test.sh unit
}

"$@"
