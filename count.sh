#!/bin/bash
#
# Count lines of code in various ways.
#
# Usage:
#   ./count.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

all() {
  echo 'BUILD/TEST AUTOMATION'
  wc -l *.sh | sort --numeric
  echo

  echo 'SHELL TEST FRAMEWORK'
  wc -l sh_spec.py | sort --numeric
  echo

  echo 'SHELL SPEC TESTS'
  wc -l tests/*.test.sh | sort --numeric
  echo

  echo 'OIL UNIT TESTS'
  wc -l {osh,core}/*_test.py | sort --numeric
  echo

  echo 'OIL'
  { ls {osh,core}/*.py; echo core/*.c; echo bin/*.py; } |
    grep -v '_test.py$' | xargs wc -l | sort --numeric
  echo

  return
  # TODO: Import docs

  echo 'DOCS'
  wc -l README.md doc/* | sort --numeric
  echo
}

# Just the parser
parser() {
  wc -l osh/{*_parse.py,lex.py,parse_lib.py} | sort -n
  echo

  # Data
  wc -l core/{*_node.py,tokens.py} | sort -n
  echo

  # Infrastructure
  wc -l core/{tdop,lexer}.py | sort -n
}

# Stuff needed to port to C+
runtime() {
  wc -l core/*_{exec,eval}.py core/{builtin,process,value}.py | sort -n
}

# count instructions, for fun
instructions() {
  # http://pepijndevos.nl/2016/08/24/x86-instruction-distribution.html

  local bin=_tmp/oil
  objdump -d $bin | cut -f3 | grep -oE "^[a-z]+" | sort | uniq -c | sort -n
}

"$@"
