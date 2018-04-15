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

# Language independent
find-src() {
  # benchmarks/testdata should be excluded
  # excluding _build, _devbuild.  Although it might be OK to test generated
  # code for tabs.
  find . '(' -type d -a -name '_*' \
          -o -name testdata \
          -o -name $PY27 \
         ')' -a -prune \
         -o \
         '(' -name '*.py' \
          -o -name '*.sh' \
          -o -name '*.asdl' \
          -o -name '*.[ch]' \
         ')' -a -print 
}

find-tabs() {
  find-src | xargs grep -n $'\t'
}

find-long-lines() {
  # Exclude URLs
  find-src | xargs grep -n '^.\{81\}' | grep -v 'http'
}

bin-flake8() {
  local ubuntu_flake8=~/.local/bin/flake8 
  if test -f "$ubuntu_flake8"; then
    $ubuntu_flake8 "$@"
  else
    # Assume it's in $PATH, like on Travis.
    flake8 "$@"
  fi
}

flake8-all() {
  local -a dirs=(asdl bin core osh opy)

  # astgen.py has a PROLOGUE which must have unused imports!
  # opcode.py triggers a flake8 bug?  Complains about def_op() when it is
  # defined.
  local -a exclude=(
    --exclude 'opy/_regtest,opy/byterun,opy/tools/astgen.py,opy/lib/opcode.py')

  # Step 1: Stop the build if there are Python syntax errors, undefined names,
  # unused imports
  local fatal_errors='E901,E999,F821,F822,F823,F401'
  bin-flake8 "${dirs[@]}" "${exclude[@]}" \
    --count --select "$fatal_errors" --show-source --statistics

  # Make unused variable fatal.  Hm there are some I want.
  #scripts/count.sh oil-osh-files | grep -F '.py' | xargs $0 bin-flake8 --select F841

  # Step 2: Style errors as warnings.

  # disable:
  # E226: missing whitespace around arithmetic -- I want to do i+1
  # E302: expected two blank lines, found 1 (sometimes one is useful).
  # E265: Although I agree with this style, some comments don't start with '# '
  # E111,E114: we use 2 space indents, not 4

  local ignored='E125,E701,E241,E121,E111,E114,E128,E262,E226,E302,E265,E290,E202,E203,C901,E261,E301,W293,E402,E116,E741,W391,E127'
  # trailing whitespace, line too long, blank lines
  local ignored_for_now='W291,E501,E303'

  # exit-zero treats all errors as warnings.  The GitHub editor is 127 chars wide
  bin-flake8 "${dirs[@]}" "${exclude[@]}" \
    --ignore "$ignored,$ignored_for_now" \
    --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
}

# Hook for travis
travis() {
  flake8-all
}

"$@"
