#!/usr/bin/env bash
#
# Run tools to maintain the coding style.
#
# Usage:
#   ./lint.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/common.sh

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

# yapf: was useful, but might cause big diffs

# disable:
# E226: missing whitespace around arithmetic -- I want to do i+1
# E302: expected two blank lines, found 1 (sometimes one is useful).
oil-pep8() {
  local temp=E501  # line too long
  pep8 --ignore E125,E701,E241,E121,E111,E128,E262,E226,E302,$temp "$@"
}

pep8-all() {
  oil-pep8 {asdl,bin,core,osh,oil,opy}/*.py "$@"
}

# Language independent
find-tabs() {
  find . '(' -name _tmp -o -name $PY27 ')' -a -prune -o \
         '(' -name '*.py' -o -name '*.sh' ')' -a -print |
    xargs grep -n $'\t'
}

"$@"
