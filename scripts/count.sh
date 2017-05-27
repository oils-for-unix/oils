#!/bin/bash
#
# Count lines ofcode in various ways.
#
# Usage:
#   ./count.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

all() {
  echo 'BUILD AUTOMATION'
  wc -l build/*.{sh,py} | sort --numeric
  echo

  echo 'TEST AUTOMATION'
  wc -l test/*.{sh,py} | sort --numeric
  echo

  echo 'SHELL SPEC TESTS'
  wc -l spec/*.test.sh | sort --numeric
  echo

  echo 'ASDL'
  wc -l asdl/{asdl_,py_meta,gen_cpp,encode,format}.py | sort --numeric
  echo

  wc -l asdl/{py_meta,encode}_test.py
  echo

  #wc -l asdl/arith_parse*.py asdl/tdop.py asdl/arith_ast.py asdl/asdl_demo.py
  #echo

  #wc -l asdl/*.cc 
  #echo

  #wc -l asdl/*.asdl
  #echo

  echo 'OIL UNIT TESTS'
  wc -l {osh,core,native,tools}/*_test.py | sort --numeric
  echo

  echo 'TOOLS'
  ls tools/*.py | grep -E -v '__init__.py$|_test.py$' | xargs wc -l | sort --numeric
  echo

  echo 'OIL'
  { ls {bin,osh,core}/*.py; ls native/*.c; } |
    grep -E -v '_gen.py$|__init__.py$|_test.py$|test_lib.py' |
    xargs wc -l | sort --numeric
  echo

  return
  # TODO: Import docs

  echo 'DOCS'
  wc -l README.md doc/* | sort --numeric
  echo
}

# Just the parser
parser() {
  echo 'Lexer/Parser'
  wc -l osh/{*_parse.py,lex.py,parse_lib.py} core/word.py | sort -n
  echo

  echo 'AST and IDs'
  wc -l osh/osh.asdl core/id_kind.py | sort -n
  echo

  echo 'Common Algorithms'
  wc -l core/{tdop,lexer}.py | sort -n
}

# Stuff we might need to hand-port
parser-port() {
  wc -l core/tdop.py osh/*_parse.py | sort -n
}

# Stuff needed to port to C+
runtime() {
  wc -l core/*_{exec,eval}.py core/{builtin,process}.py core/runtime.asdl | sort -n
}

# count instructions, for fun
instructions() {
  # http://pepijndevos.nl/2016/08/24/x86-instruction-distribution.html

  local bin=_tmp/oil
  objdump -d $bin | cut -f3 | grep -oE "^[a-z]+" | sort | uniq -c | sort -n
}

imports() {
  grep --no-filename import */*.py | sort | uniq -c | sort -n
}

"$@"
