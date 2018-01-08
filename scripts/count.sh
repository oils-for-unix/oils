#!/usr/bin/env bash
#
# Count lines ofcode in various ways.
#
# Usage:
#   ./count.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

filter-py() {
  grep -E -v '__init__.py$|_test.py$' 
}

# TODO: Sum up all the support material.  It's more than Oil itself!  Turn
# everything into an array.  An hash table of arrays would be useful here.
all() {
  echo 'BUILD AUTOMATION'
  wc -l build/*.{sh,py} Makefile configure install | filter-py | sort --numeric
  echo

  echo 'TEST AUTOMATION'
  wc -l test/*.{sh,py,R} | filter-py | sort --numeric
  echo

  echo 'RELEASE AUTOMATION'
  wc -l scripts/release.sh | sort --numeric
  echo

  echo 'BENCHMARKS'
  wc -l benchmarks/*.{sh,py,R} | sort --numeric
  echo

  echo 'SPEC TESTS'
  wc -l spec/*.test.sh | sort --numeric
  echo

  echo 'GOLD TESTS'
  wc -l gold/*.sh | sort --numeric
  echo

  echo 'ASDL'
  wc -l asdl/{asdl_*,const,py_meta,encode,format}.py | sort --numeric
  echo

  echo 'CODE GENERATORS'
  wc -l asdl/gen_*.py */*_gen.py | sort --numeric
  echo

  echo 'GENERATED CODE'
  wc -l _devbuild/gen/*.{py,h} | sort --numeric
  echo

  echo 'TOOLS'
  ls tools/*.py | filter-py | xargs wc -l | sort --numeric
  echo

  echo 'WEB'
  ls web/*.js web/*/*.{js,py} | xargs wc -l | sort --numeric
  echo

  echo 'OTHER UNIT TESTS'
  wc -l {build,test,asdl,tools}/*_test.py | sort --numeric
  echo

  echo 'OIL UNIT TESTS'
  wc -l {osh,core,native,tools}/*_test.py | sort --numeric
  echo

  echo 'OIL'
  { ls {bin,osh,core}/*.py native/*.c osh/osh.asdl core/runtime.asdl; } |
    filter-py | grep -E -v '_gen.py$|test_lib.py' |
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
  echo 'AST and IDs'
  wc -l osh/osh.asdl core/id_kind.py | sort -n
  echo

  echo 'Lexer / Parser'
  wc -l osh/{*_parse.py,lex.py,parse_lib.py} core/word.py | sort -n
  echo

  echo 'Compiler / Middle End'
  wc -l core/{braces,word_compile}.py | sort -n
  echo

  echo 'Common Algorithms'
  wc -l core/{tdop,lexer}.py | sort -n
  echo

  echo 'Utilities'
  wc -l core/{alloc,ui,reader}.py | sort -n
  echo
}

# Stuff we might need to hand-port
parser-port() {
  wc -l core/tdop.py osh/*_parse.py | sort -n
}

runtime() {
  # NOTE: braces.py contains both parsing and runtime.  It is a  middle stage.

  echo 'Runtime'
  wc -l core/{process,state}.py core/runtime.asdl | sort -n
  echo

  # NOTE: These may turn into compilers
  echo 'Evaluators'
  wc -l core/*_{exec,eval}.py | sort -n
  echo

  echo 'Builtins'
  wc -l core/{builtin,test_builtin}.py
  echo

  echo 'Libraries'
  wc -l core/{args,glob_,legacy,libstr}.py | sort -n
  echo
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

# For the compiler, see what's at the top level.
top-level() {
  grep '^[a-zA-Z]' {core,osh}/*.py \
    | grep -v '_test.py'  \
    | egrep -v ':import|from|class|def'  # note: colon is from grep output
}

"$@"
