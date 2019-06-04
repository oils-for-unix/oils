#!/bin/bash
#
# Usage:
#   ./count.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

_count() {
  grep -v '_test.py$' | xargs wc -l | sort -n
}

# 8700 lines for tokenizer -> tokens -> parser -> homogeneous nodes ->
# transformer -> ast -> compiler -> byte code
all() {
  echo COMMON
  echo opy_main.py | _count
  echo

  echo GRAMMAR
  echo py27.grammar | _count
  echo

  # ast is generated
  echo COMPILER2
  ls compiler2/*.py | grep -v ast.py | _count
  echo

  echo STDLIB
  echo lib/*.py | _count
  echo

  echo GENERATED CODE
  wc -l compiler2/ast.py
  echo

  echo BYTERUN
  ls byterun/*.py | grep -v 'test' | _count
  echo

  echo MISC
  echo {misc,tools}/*.py | _count
  echo

  echo UNIT TESTS
  echo */*_test.py | xargs wc -l | sort -n
  echo

  echo SCRIPTS
  echo *.sh */*.sh | xargs ls | grep -v '^old/' | _count
  echo
}

ovm() {
  wc -l opy/*/ovm*.py
}

"$@"
