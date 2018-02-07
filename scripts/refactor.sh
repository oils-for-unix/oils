#!/usr/bin/env bash
#
# Usage:
#   ./refactor.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# TODO:
# Rparen -> RParen, Dgreat -> DGreat, Colon_Hyphen -> ColonHyphen, etc.
# IGNORED_LINECONT -> IGNORED_LineCont

# LIT -> Lit
# LEFT -> Left
# LEFT -> Left

# VS -> VSub
# VS_TEST VTest
# VS_UNARY VUnary 
# VS_OP VOp
# 


change-kind() {
  local kind=$1
  local kind2=${2:-$kind}

  # First make it all lower case
  sed -r -i "s/${kind}_([A-Z]+)/Id.${kind2}_\\L\\1/g" */*.py

  # Now make the first one upper case
  sed -r -i "s/${kind}_([a-zA-Z]+)/${kind2}_\\u\\1/g" */*.py
}

k2() {
  local kind=$1
  local lower=${kind,,}

  local title=${lower^}
  local replace=${2:-$title}

  sed -r -i "s/Id.${kind}_/Id.${replace}_/g" */*.py
  sed -r -i "s/TokenKind.${kind}/TokenKind.${replace}/g" */*.py
}

replace() {
  local file=$1

  # NOTE: Escaping here is messed up.  sed doesn't have --name like awk?
  while read pat replace; do
    sed -r -i "s/${pat}/${replace}/g" */*.py
  done < $file
}

replace2() {
  #sed -r -i "s/^from core.id_kind import/from osh.meta import/g" */*.py
  #sed -r -i "s/^from osh import ast_ as ast/from osh.meta import ast/g" */*.py
  sed -r -i "s/^from core import runtime/from osh.meta import runtime/g" */*.py
}

trailing-ws() {
  sed -r -i 's/[ ]+$//g' "$@"
}

"$@"
