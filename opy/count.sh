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

  echo LEXER, PARSER GENERATOR, AND GRAMMR
  echo pytree.py pgen2/*.py py27.grammar | _count
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

# Hm there are 119 total opcodes, but these files only use 38, 37, 36, and 23.
# Interesting.

# With opy: 39, 38, 35, 24.  Oh so there's 1 more or one less.  Interesting!
# TODO: diff them.

# differences: 
# PRINT_ITEM, PRINT_NEWLINE
# UNARY_NEGATIVE
# UNARY_NOT: big differences in magnitudes!  Is this a bug?

readonly PARSER=(osh/{cmd,bool,word,arith}_parse.pyc)

opcodes-comparison() {
  for pyc in "${PARSER[@]}"; do
    echo
    echo "=== $pyc ==="
    echo

    bin/opyc dis $pyc cpython.txt >/dev/null
    bin/opyc dis _tmp/oil-with-opy/$pyc opy.txt >/dev/null
    local diff=${DIFF:-diff -u}
    $diff {cpython,opy}.txt
  done
}

opcodes() {
  for pyc in "${PARSER[@]}"; do
    echo
    echo "=== $pyc ==="
    echo

    bin/opyc dis _tmp/oil-with-opy/$pyc
  done
}

"$@"
