#!/bin/bash
#
# Usage:
#   ./count.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

_count() {
  xargs wc -l | sort -n
}

# 8700 lines for tokenizer -> tokens -> parser -> homogeneous nodes ->
# transformer -> ast -> compiler -> byte code
all() {
  echo COMMON
  echo opy_main.py util_opy.py | _count
  echo

  echo LEXER, PARSER GENERATOR, AND GRAMMR
  echo pytree.py pgen2/*.py py27.grammar | _count
  echo

  # ast is generated
  echo COMPILER2
  ls compiler2/*.py | grep -v ast.py | xargs wc -l | sort -n
  echo

  echo GENERATED CODE
  wc -l compiler2/ast.py
  echo

  echo BYTERUN
  ls byterun/*.py | grep -v 'test' | xargs wc -l | sort -n
  echo

  echo MISC
  echo {misc,tools}/*.py | _count
  echo

  echo SCRIPTS
  echo *.sh */*.sh | _count
  echo
}

# Hm there are 119 total opcodes, but these files only use 38, 37, 36, and 23.
# Interesting.

# With opy: 39, 38, 35, 24.  Oh so there's 1 more or one less.  Interesting!
# TODO: diff them.

opcodes() {
  for prefix in '' _tmp/oil-with-opy/; do
    for pyc in \
      ${prefix}osh/{cmd,bool,word,arith}_parse.pyc; do
      echo $pyc
      bin/opyc dis $pyc | tail -n 1 
    done
  done
}

"$@"
