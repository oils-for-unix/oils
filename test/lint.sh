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

# After 'pip install pep8' on Ubunu, it's in ~/.local.
bin-pep8() {
  ~/.local/bin/pep8 "$@"
}

# disable:
# E226: missing whitespace around arithmetic -- I want to do i+1
# E302: expected two blank lines, found 1 (sometimes one is useful).
# E265: Although I agree with this style, some comments don't start with '# '
# E111,E114: we use 2 space indents, not 4
oil-pep8() {
  # These could be enabled.
  local temp=W291,E501,E303  # trailing whitespace, line too long, blank lines
  bin-pep8 --ignore E125,E701,E241,E121,E111,E114,E128,E262,E226,E302,E265,$temp "$@"
}

pep8-all() {
  oil-pep8 {asdl,bin,core,osh}/*.py "$@"
}

# Language independent
find-tabs() {
  # benchmarks/testdata should be excluded
  find . '(' -name _tmp \
          -o -name _chroot \
          -o -name _deps \
          -o -name testdata \
          -o -name $PY27 \
         ')' \
         -a -prune -o \
         '(' -name '*.py' -o -name '*.sh' ')' -a -print |
    xargs grep -n $'\t'
}

"$@"
