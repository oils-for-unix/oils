#!/bin/bash
#
# Usage:
#   ./refactor.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

replace() {
  #sed -r -i 's/UNDEFINED_(.*)/Id.UNDEFINED_\1/g' */*.py

  #sed -r -i 's/UNDEFINED_TOK/Id.UNDEFINED_Tok/g' */*.py

  #sed -r -i 's/UNKNOWN_TOK/Id.UNKNOWN_Tok/g' */*.py

  # http://stackoverflow.com/questions/1538676/uppercasing-first-letter-of-words-using-sed
  # http://stackoverflow.com/questions/4569825/sed-one-liner-to-convert-all-uppercase-to-lowercase
  # GNU extension: \u next character of match

  # Finally, as a GNU `sed' extension, you can include a special sequence made
  # of a backslash and one of the letters `L', `l', `U', `u', or `E'.  The
  # meaning is as follows:
 
  # First make it all lower case
  sed -r -i 's/Eof_([A-Z]+)/Id.Eof_\L\1/g' */*.py

  # Now make the first one upper case
  sed -r -i 's/Eof_([a-zA-Z]+)/Eof_\u\1/g' */*.py
}

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

  while read pat replace; do
    sed -r -i "s/${pat}/${replace}/g" */*.py
  done < $file
}

"$@"
