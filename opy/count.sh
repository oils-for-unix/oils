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

  echo PARSER GENERATOR
  echo pytree.py pgen2/*.py | _count
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

"$@"
