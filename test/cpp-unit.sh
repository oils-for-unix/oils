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

  mycpp/test.sh unit  # uses Ninja

  # This is part of build/dev.sh oil-cpp
  build/codegen.sh ast-id-lex  # id.h, osh-types.h, osh-lex.h
  build/codegen.sh flag-gen-cpp  # _build/cpp/arg_types.h
  build/dev.sh oil-asdl-to-cpp  # unit tests depend on id_kind_asdl.h, etc.

  cpp/test.sh unit

  asdl/test.sh unit
}

"$@"
