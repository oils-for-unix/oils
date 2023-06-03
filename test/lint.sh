#!/usr/bin/env bash
#
# Run tools to maintain the coding style.
#
# Usage:
#   test/lint.sh <function name>

set -o nounset
set -o pipefail
set -o errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
readonly REPO_ROOT

source build/common.sh
source devtools/run-task.sh  # run-task

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
  # See //.clang-format for the style config.
  $CLANG_DIR/bin/clang-format --style=file "$@"
}

readonly -a CPP_FILES=(
  {asdl,core}/*.cc
  benchmarks/*.c
  cpp/*.{c,cc,h}
  mycpp/*.{cc,h} 
  mycpp/demo/*.{cc,h}
  demo/*.c

  # Could add pyext, but they have sort of a Python style
  # pyext/fanos.c
)

cpp-files() {
  shopt -s nullglob
  for file in "${CPP_FILES[@]}"; do

    echo $file
  done
}

format-cpp() {
  # see build/common.sh
  if test -n "$CLANG_IS_MISSING"; then
    log ''
    log "  *** $0: Did not find $CLANG_DIR_1"
    log "  *** Run deps/from-binary.sh to get it"
    log ''
    return 1
  fi

  cpp-files | egrep -v 'greatest.h' | xargs -- $0 clang-format -i 
  git diff
}

test-asdl-format() {
  ### Test how clang-format would like our generated code

  local file=${1:-_gen/asdl/hnode.asdl.h}

  local tmp=_tmp/hnode
  clang-format $file > $tmp
  diff -u $file $tmp
}

#
# Python
#

find-prune() {
  ### find real source files

  # benchmarks/testdata should be excluded
  # excluding _build, _devbuild.  Although it might be OK to test generated
  # code for tabs.
  find . '(' -type d -a -name '_*' \
          -o -name testdata \
          -o -name $PY27 \
         ')' -a -prune \
         "$@"
}

find-src-files() {
  find-prune \
    -o -type f -a \
   '(' -name '*.py' \
    -o -name '*.sh' \
    -o -name '*.asdl' \
    -o -name '*.[ch]' \
    -o -name '*.cc' \
   ')' -a -print 
}

find-tabs() {
  find-src-files | xargs grep -n $'\t'
}

find-long-lines() {
  # Exclude URLs
  find-src-files | xargs grep -n '^.\{81\}' | grep -v 'http'
}

bin-flake8() {
  python2 -m flake8 "$@"
}

# Just do a single file
flake8-one() {
  bin-flake8 --ignore 'E111,E114,E226,E265' "$@"
}

flake8-all() {
  local -a dirs=(asdl bin core ysh osh opy ovm2 tools)

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

#
# More Python, including Python 3
#

install-black() {
  ../oil_DEPS/python3 -m pip install black
}

mycpp-files() {
  for f in mycpp/*.py; do
    case $f in
      */NINJA_subgraph.py)
        continue
        ;;
    esac

    echo $f
  done
}

# Black fixes indentation, but also turns all our single quotes into double
# quotes
run-black() {
  mycpp-files | xargs --verbose -- ../oil_DEPS/python3 -m black
}


install-yapf() {
  pip3 install yapf docformatter
}

run-yapf-3() {
  ### Run yapf on Python 3 code
  mycpp-files | xargs python3 -m yapf -i
}

py2-files-to-format() {
  for name in {asdl,core,frontend,osh,tools,ysh}/*.py; do
    echo $name
  done | grep -v 'NINJA_subgraph'  # leave out for now
}

run-yapf-2() {
  ### Run yapf on Python 2 code

  # These files originally had 4 space indentation, but it got inconsistent
  time py2-files-to-format \
    | xargs --verbose -- python3 -m yapf -i --style='{based_on_style: google: indent_width: 4}'

  time py2-files-to-format \
    | xargs --verbose -- python3 -m docformatter --in-place
}

#
# Main
#

# Hook for soil
soil-run() {
  if test -n "${TRAVIS_SKIP:-}"; then
    echo "TRAVIS_SKIP: Skipping $0"
    return
  fi

  flake8-all

  check-shebangs
}

#
# Adjust and Check shebang lines.  It matters for developers on different distros.
#

find-files-to-lint() {
  ### Similar to find-prune / find-src-files, but used for Soil checks

  # don't touch mycpp yet because it's in Python 3
  # build has build/dynamic_deps.py which needs the -S
  find . \
    -name '_*' -a -prune -o \
    -name 'Python-*' -a -prune -o \
    "$@"
}

find-py() {
  find-files-to-lint \
    -name 'build' -a -prune -o \
    -name '*.py' -a -print "$@"
}

find-sh() {
  find-files-to-lint -name '*.sh' -a -print "$@"
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
#
# e.g. cat edit.list, change the first line

replace-py-shebang() {
  sed -i '1c#!/usr/bin/env python2' "$@"
}

replace-bash-shebang() {
  sed -i '1c#!/usr/bin/env bash' "$@"
}

# NOTE: no ^ anchor because of print-first-line

readonly BAD_PY='#!.*/usr/bin/python'
readonly BAD_BASH='#!.*/bin/bash'

bad-py() {
  find-py -a -print | xargs -- egrep "$BAD_PY"
  #grep '^#!.*/bin/bash ' */*.sh

  find-py -a -print | xargs -- egrep -l "$BAD_PY" | xargs $0 replace-py-shebang
}

bad-bash() {
  # these files don't need shebangs
  #grep -l '^#!' spec/*.test.sh | xargs -- sed -i '1d'

  #find-sh -a -print | xargs -- grep "$BAD_BASH"

  find-sh -a -print | xargs -- egrep -l "$BAD_BASH" | xargs $0 replace-bash-shebang
}

print-first-line() {
  local path=$1

  read line < "$path"
  echo "$path: $line"  # like grep output
}

check-shebangs() {
  set +o errexit

  if true; then
    find-py | xargs -d $'\n' -n 1 -- $0 print-first-line | egrep "$BAD_PY"
    if test $? -ne 1; then
      die "FAIL: Found bad Python shebangs"
    fi
  fi

  find-sh | xargs -d $'\n' -n 1 -- $0 print-first-line | egrep "$BAD_BASH"
  if test $? -ne 1; then
    die "FAIL: Found bad bash shebangs"
  fi

  echo 'PASS: check-shebangs'
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
  grep ^class {osh,core,ysh,frontend}/*.py \
    | egrep -v '_test|object'
}

# 18 unique base classes.
# TODO: Maybe extract this automatically with OPy?
# Or does the MyPy AST have enough?
# You can collect method defs in the decl phase.  Or in the forward_decl phase?

base-classes() {
  inheritance | egrep -o '\(.*\)' | sort | uniq -c | sort -n
}

translation() {
  set +o errexit

  metrics/source-code.sh osh-files \
    | xargs egrep -n 'IndexError|KeyError'
  local status=$?

  echo

  # 4 occurrences
  # source builtin, core/process.py, etc.

  metrics/source-code.sh osh-files \
    | xargs egrep -n 'finally:'
    #| xargs egrep -n -A 1 'finally:'
}
 
run-task "$@"
