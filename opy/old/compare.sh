#!/usr/bin/env bash
#
# Usage:
#   ./compare.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly PY27=~/src/Python-2.7.6
readonly PY36=~/src/Python-3.6.1

readonly DIFF=${DIFF:-diff -u}

ceval() {
  # 4900 lines vs 5500 lines.  Wow
  wc -l {$PY27,$PY36}/Python/ceval.c
  return
  $DIFF {$PY27,$PY36}/Python/ceval.c
}

ccompile() {
  # 4000 vs 5300 lines.  Big increase.  But it depends on the opcodes.
  wc -l {$PY27,$PY36}/Python/compile.c
}

opcodes() {
  #cp -v $PY27/Lib/opcode.py _tmp/opcode27.py
  #cp -v $PY36/Lib/opcode.py _tmp/opcode36.py

  $DIFF _tmp/opcode{27,36}.py
  return

  cp $PY27/Lib/dis.py _tmp/dis27.py
  cp $PY36/Lib/dis.py _tmp/dis36.py

  $DIFF _tmp/dis{27,36}.py
}

2to3-grammar() {
  # The compiler package was written for a different grammar!
  $DIFF $PY27/Grammar/Grammar 2to3.grammar 
}

# pgen2 has BACKQUOTE = 25.  No main.
tokens() {
  $DIFF token.py pgen2/token.py
}

# This is very different -- is it Python 2 vs. Python 3?
tokenize() {
  $DIFF tokenize.py pgen2/tokenize.py
}

compiler2() {
  #diff -u $PY27/Lib/compiler/ compiler2

  # The version we're actually running
  diff -u /usr/lib/python2.7/compiler/ compiler2
}

compiler26-27() {
  diff -u ~/src/Python-2.{6,7}.9/Lib/compiler/
}

compiler27() {
  diff -u ~/src/Python-2.7.{2,9}/Lib/compiler/
}

set27() {
  diff -u ~/src/Python-2.7.{2,3}/Objects/setobject.c
}

if test $(basename $0) = compare.sh; then
  "$@"
fi
