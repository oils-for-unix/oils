#!/bin/bash
#
# Run tools to maintain the coding style.
#
# Usage:
#   ./lint.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

get-cpplint() {
  mkdir -p _tmp
  wget --directory _tmp \
    https://raw.githubusercontent.com/google/styleguide/gh-pages/cpplint/cpplint.py
  chmod +x _tmp/cpplint.py
}

cpplint() {
  _tmp/cpplint.py --filter -readability/todo,-legal/copyright \
    *.{cc,h} shell/*.{cc,h}
}

clang-format() {
  #$CLANG_DIR/bin/clang-format -style=Google "$@"

  # We have a lot of switch statements, and the extra indent doesn't help.
  $CLANG_DIR/bin/clang-format \
    -style="{BasedOnStyle: Google, IndentCaseLabels: false}" \
    "$@"
}

# TODO: -i
# Integrate with editor.
format-oil() {
  #clang-format -i shell/util.cc shell/util.h shell/string_piece.h
  #clang-format -i shell/lex.re2c.cc shell/lex.h

  clang-format -i *.{cc,h} shell/*.{cc,h}
  git diff
}

format-demo() {
  clang-format -i demo/*.cc
  git diff
}

#
# Python
#

# yapf: useful
# pep8: useful


"$@"
