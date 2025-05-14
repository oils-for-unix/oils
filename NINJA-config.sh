#!/usr/bin/env bash
#
# Creates build.ninja.  Crawls dynamic dependencies.
#
# Usage:
#   ./NINJA-config.sh

set -o nounset
set -o pipefail
set -o errexit

source build/dev-shell.sh  # python2 in $PATH
source build/dynamic-deps.sh  # py-tool, etc

PY_TOOL=(
  asdl.asdl_main
  core.optview_gen
  frontend.consts_gen
  frontend.flag_gen
  frontend.lexer_gen
  frontend.option_gen
  ysh.grammar_gen
  osh.arith_parse_gen
  frontend.signal_gen
  cpp.embedded_file_gen

  # translated
  bin.hello
)

BIN=(
  yaks.yaks_main  # Experimental IR to C++ translator
  bin.osh_parse
  bin.osh_eval
  bin.oils_for_unix
)

# Create a dir structure htat looks like this:

# _build/NINJA/  # Part of the Ninja graph
#   asdl.asdl_main/
#     all-pairs.txt
#     deps.txt
#   bin.hello/
#     all-pairs.txt
#     deps.txt
#   bin.oils_for_unix/
#     all-pairs.txt
#     typecheck.txt  # special case
#     deps.txt
#
# Related:
#   prebuilt/
#     ninja/
#       mycpp.mycpp_main/
#     dynamic-deps/
#       filter-py-tool
#   mycpp/
#     examples/
#       parse.translate.txt
#       parse.typecheck.txt
#
# Should be parse.typecheck.txt and parse.deps.txt
#
# New structure
#   bin/
#     oils_for_unix.py
#     oils_for_unix_preamble.h
#     oils_for_unix.typecheck-filter.txt
#     oils_for_unix.deps-filter.txt
#   mycpp/
#     examples/
#       parse.py
#       parse_preamble.h
#       parse.deps-filter.txt
#
# All of these are optional, except deps-filter?
# The default deps-filter can be in prebuilt/ perhaps

main() {
  mkdir -p _build/NINJA

  # Implicit dependencies for tools
  for mod in "${PY_TOOL[@]}"; do
    py-tool $mod
  done

  # Explicit dependencies for translating and type checking
  # Baked into mycpp/NINJA.
  for mod in "${BIN[@]}"; do
    typecheck-translate $mod
  done

  echo DEPS prebuilt/ninja/*/deps.txt
  echo

  # Reads the deps.txt files above
  PYTHONPATH=. build/ninja_main.py
}

main "$@"
