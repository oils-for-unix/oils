#!/usr/bin/env bash
#
# Run tools to maintain the coding style.
#
# Usage:
#   ./lint.sh <function name>

set -o nounset
set -o pipefail
set -o errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

source build/common.sh

# ubuntu names
install-flake8() {
  sudo apt install python-pip
  pip install flake8
}

get-cpplint() {
  mkdir -p _tmp
  wget --directory _tmp \
    https://raw.githubusercontent.com/google/styleguide/gh-pages/cpplint/cpplint.py
  chmod +x _tmp/cpplint.py
}

cpplint() {
  # we don't have subdir names on the header guard
  _tmp/cpplint.py --filter \
    -readability/todo,-legal/copyright,-build/header_guard,-build/include,-whitespace/comments "$@"
}

clang-format() {
  #$CLANG_DIR/bin/clang-format -style=Google "$@"

  # I like consistent Python-style functions and blocks, e.g. not if (x) return
  local style='{ BasedOnStyle: Google,
      IndentCaseLabels: false,
      AllowShortFunctionsOnASingleLine: None,
      AllowShortBlocksOnASingleLine: false,
    }
  '
  # We have a lot of switch statements, and the extra indent doesn't help.
  $CLANG_DIR/bin/clang-format -style="$style" "$@"
}

# Not ready to do this yet?
# I don't like one liners like Constructor : v_() {}
format-oil() {
  clang-format -i cpp/*.{cc,h} mycpp/*.{cc,h}
  git diff
}

#
# Python
#

# yapf: was useful, but might cause big diffs

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

_parse-one-oil() {
  local path=$1
  echo $path
  if ! bin/osh -O all:oil -n $path >/dev/null; then
    return 255  # stop xargs
  fi
}

all-oil-parse() {
  ### Make sure they parse with shopt -s all:oil
  ### Will NOT Parse with all:nice.
  find-src |
    grep '.sh$' |
    egrep -v 'spec/|/parse-errors/' |
    xargs -n 1 -- $0 _parse-one-oil
}

bin-flake8() {
  local ubuntu_flake8=~/.local/bin/flake8 
  if test -f "$ubuntu_flake8"; then
    $ubuntu_flake8 "$@"
  else
    python2 -m flake8 "$@"
  fi
}

# Just do a single file
flake8-one() {
  bin-flake8 --ignore 'E111,E114,E226,E265' "$@"
}

flake8-all() {
  local -a dirs=(asdl bin core oil_lang osh opy ovm2 tools)

  # astgen.py has a PROLOGUE which must have unused imports!
  # opcode.py triggers a flake8 bug?  Complains about def_op() when it is
  # defined.
  # _abbrev.py modules are concatenated, and don't need to check on their own.
  local -a exclude=(
    --exclude 'tools/find,tools/xargs,opy/_*,opy/byterun,opy/tools/astgen.py,opy/lib/opcode.py,*/*_abbrev.py')

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
  if test -n "${TRAVIS_SKIP:-}"; then
    echo "TRAVIS_SKIP: Skipping $0"
    return
  fi

  flake8-all
}

#
# Adjust and Check shebang lines.  It matters for developers on different distros.
#

find-py() {
  # don't touch mycpp yet because it's in Python 3
  # build has build/app_deps.py which needs the -S
  find \
    -name '_*' -a -prune -o \
    -name 'Python-*' -a -prune -o \
    -name 'mycpp' -a -prune -o \
    -name 'build' -a -prune -o \
    -name '*.py' "$@"
}

print-if-has-shebang() {
  read first < $1
  [[ "$first" == '#!'* ]]  && echo $1
}

not-executable() {
  find-py -a ! -executable -a -print | xargs -n 1 -- $0 print-if-has-shebang
}

executable-py() {
  find-py -a -executable -a -print | xargs -n 1 -- echo
}

# Make all shebangs consistent.
# - Specify python2 because on some distros 'python' is python3
# - Use /usr/bin/env because it works better with virtualenv?
#
# https://stackoverflow.com/questions/9309940/sed-replace-first-line
replace-shebang() {
  # e.g. cat edit.list, change the first line
  sed -i '1c#!/usr/bin/env python2' "$@"
}

#
# sprintf -- What do we need in mycpp?
#

sp-formats() {
  egrep --no-filename --only-matching '%.' */*.py | sort | uniq -c | sort -n
}

# 122 instances of these.  %() for named
sp-rare() {
  egrep --color=always '%[^srd ]' */*.py  | egrep -v 'Python-|_test.py'
}

#
# inherit
#

# 56 instances of inheritance
inheritance() {
  grep ^class {osh,core,oil_lang,frontend}/*.py \
    | egrep -v '_test|object'
}

# 18 unique base classes.
# TODO: Maybe extract this automatically with OPy?
# Or does the MyPy AST have enough?
# You can collect method defs in the decl phase.  Or in the forward_decl phase?

base-classes() {
  inheritance | egrep -o '\(.*\)' | sort | uniq -c | sort -n
}
 
"$@"
