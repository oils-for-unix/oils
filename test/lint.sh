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
source build/dev-shell.sh  # python2 and python3
source devtools/common.sh  # banner
source devtools/run-task.sh  # run-task

readonly -a CODE_DIRS=(asdl bin core data_lang frontend osh tools ysh)

#
# C++
#

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

#
# pyflakes-based lint
#

oils-lint() {
  local lang=$1  # py2 or py3
  shift

  PYTHONPATH=.:~/wedge/oils-for-unix.org/pkg/pyflakes/2.4.0 test/${lang}_lint.py "$@"
  #PYTHONPATH=.:vendor/pyflakes-2.4.0 test/oils_lint.py "$@"
}

py2-lint() {
  oils-lint py2 "$@"
}

py3-lint() {
  oils-lint py3 "$@"
}

py2() {
  banner 'Linting Python 2 code'

  # syntax_abbrev.py doesn't stand alone
  py2-files-to-format | grep -v '_abbrev.py' | xargs $0 py2-lint
}

py3-files() {
  for f in mycpp/*.py; do
    echo $f
  done
}

py3() {
  banner 'Linting Python 3 code'

  py3-files | xargs $0 py3-lint
}

all-py() {
  py2
  py3
}

#
# More Python, including Python 3
#

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

py2-files-to-format() {
  for dir in "${CODE_DIRS[@]}"; do
    for name in $dir/*.py; do
      echo $name
    done
  done | grep -v 'NINJA_subgraph'  # leave out for now
}

run-docformatter() {
  ### Format docstrings

  # Only done as a ONE OFF to indent docstrings after yapf-2
  # Because it tends to mangle comments, e.g. grammar comments in
  # ysh/expr_to_ast.py
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

  #flake8-all

  # Our new lint script
  all-py

  check-shebangs
}

#
# Adjust and Check shebang lines.  It matters for developers on different distros.
#

find-files-to-lint() {
  ### Similar to find-prune / find-src-files

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
