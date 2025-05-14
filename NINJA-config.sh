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
)

BIN=(
  # translated
  bin.hello
  bin.hello_mylib
  bin.oils_for_unix
  mycpp.examples.parse
)

# These special cases should go away
SPECIAL_BIN=(
  yaks.yaks_main  # Experimental IR to C++ translator
  bin.osh_parse
  bin.osh_eval
)

# A binary looks like this:
#
#   bin/
#     hello.py          # no preamble
#                       # uses build/default.{typecheck,translate}-filter.txt
#     oils_for_unix.py
#     oils_for_unix_preamble.h
#     oils_for_unix.typecheck-filter.txt
#     oils_for_unix.translate-filter.txt
#   mycpp/
#     examples/
#       parse.py
#       parse_preamble.h
#       # TODO: {translate,typecheck}-filter

# Supporting files:
#
# _build/NINJA/  # Part of the Ninja graph
#   asdl.asdl_main/
#     all-pairs.txt
#     deps.txt
#   bin.hello/
#     all-pairs.txt
#     typecheck.txt
#     translate.txt
#   bin.oils_for_unix/
#     all-pairs.txt
#     typecheck.txt
#     translate.txt
#
# Related:
#   prebuilt/
#     ninja/
#       mycpp.mycpp_main/
#       pea.pea_main/

main() {
  mkdir -p _build/NINJA

  # Implicit dependencies for tools
  for mod in "${PY_TOOL[@]}"; do
    py-tool $mod
  done

  # Use filters next to the binary, or the defaults
  for mod in "${BIN[@]}"; do
    typecheck-translate $mod
  done

  # Legacy: use Oils
  for mod in "${SPECIAL_BIN[@]}"; do
    typecheck-translate $mod \
      bin/oils_for_unix.typecheck-filter.txt \
      bin/oils_for_unix.translate-filter.txt
  done

  echo DEPS prebuilt/ninja/*/deps.txt
  echo

  # Reads the deps.txt files above
  PYTHONPATH=. build/ninja_main.py
}

main "$@"
