#!/bin/bash
#
# Usage:
#   ./typed.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

deps() {
  set -x
  #pip install typing pyannotate

  # got error with 0.67.0
  pip3 install 'mypy==0.660'
}

mypy() { ~/.local/bin/mypy "$@"; }
# This has a bug
#pyannotate() { ~/.local/bin/pyannotate "$@"; }

readonly PYANN_REPO=~/git/oilshell/pyannotate/

pyann-patched() {
  local tool=$PYANN_REPO/pyannotate_tools/annotations
  export PYTHONPATH=$PYANN_REPO
  # --dump can help
  python $tool "$@"
}

typecheck() {
  mypy --py2 "$@"
}

# --no-strict-optional issues
# - simple sum type might be None, but generated PrettyTree() method uses
#   obj.name

iter-demo-asdl() {
  asdl/run.sh gen-typed-demo-asdl
  typecheck --strict \
    _devbuild/gen/typed_demo_asdl.py asdl/typed_demo.py

  PYTHONPATH=. asdl/typed_demo.py "$@"
}

check-arith() {
  local strict='--strict'
  MYPYPATH=. PYTHONPATH=. typecheck $strict \
    asdl/typed_arith_parse.py asdl/typed_arith_parse_test.py asdl/tdop.py
}

iter-arith-asdl() {
  asdl/run.sh gen-typed-arith-asdl
  check-arith

  export PYTHONPATH=. 
  asdl/typed_arith_parse_test.py

  echo '---'
  asdl/typed_arith_parse.py parse '40+2'
  echo

  echo '---'
  asdl/typed_arith_parse.py eval '40+2+5'
  echo
}

# Alias for convenience
check-osh-parse() {
  types/osh-parse.sh check-some
}

collect-types() {
  export PYTHONPATH=".:$PYANN_REPO"
  types/pyann_driver.py "$@"

  ls -l type_info.json
  wc -l type_info.json
}

peek-type-info() {
  grep path type_info.json | sort | uniq -c | sort -n
}

apply-types() {
  #local -a files=( asdl/tdop.py asdl/typed_arith_parse*.py )

  #local -a files=( core/util.py asdl/runtime.py )
  #local -a files=(asdl/format.py )
  #local -a files=(
  #  frontend/lexer.py frontend/match.py frontend/reader.py core/alloc.py
  #  core/meta.py )
  #local -a files=(osh/word.py)

  #local -a files=(frontend/parse_lib.py)
  #local -a files=(core/meta.py core/id_kind.py frontend/tdop.py osh/arith_parse.py)
  local -a files=(core/id_kind.py)
  #local -a files=(osh/bool_parse.py)
  #local -a files=(osh/word_parse.py)
  #local -a files=(osh/cmd_parse.py)
  #local -a files=(core/ui.py)

  #local -a files=( $(cat _tmp/osh-parse-src.txt | grep -v syntax_asdl.py ) )

  pyann-patched --type-info type_info.json "${files[@]}" "$@"
}

sub() {
  local f=$1
  types/refactor.py sub < $f > _tmp/sub.txt
  diff -u _tmp/sub.txt $f
}

audit-hacks() {
  # I used a trailing _ in a couple places to indicates hacks
  # A MyPy upgrade might fix this?
  egrep -n --context 1 '[a-z]+_ ' osh/*_parse.py
}

"$@"
