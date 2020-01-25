#!/usr/bin/env bash
#
# Usage:
#   ./refactor.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

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

# Execute a bunch of find/replace pairs in a text file.
replace() {
  local file=$1
  local include_asdl=${2:-}

  # NOTE: Escaping here is messed up.  sed doesn't have --name like awk?
  # To match literal parentheses I had to double-escape like this
  # (shell-escape, then sed-escape).
  # MakeMatcher\\(\\) MATCHER

  local -a files=( */*.py )
  if test -n "$include_asdl"; then
    files+=( */*.asdl )
  fi

  while read pat replace; do
    sed -r -i "s/${pat}/${replace}/g" "${files[@]}"

    # word-anchored version
    #sed -r -i "s/\b${pat}\b/${replace}/g" "${files[@]}"
  done < $file
}

replace2() {
  #sed -r -i "s/^from osh import parse_lib/from frontend import parse_lib/g" */*.py
  #sed -r -i "s/^from core import libstr/from osh import string_ops/g" */*.py
  #sed -r -i "s/^from osh import word$/from osh import word_/g" */*.py
  #sed -r -i 's/from _devbuild.gen.syntax_asdl import word as osh_word/from _devbuild.gen.syntax_asdl import word/g' */*.py
  #sed -r -i 's/osh_word/word/g' */*.py

  if test -n ''; then
    sed -r -i 's/bool_expr.BoolUnary/bool_expr.Unary/g' */*.py
    sed -r -i 's/bool_expr.BoolBinary/bool_expr.Binary/g' */*.py
    sed -r -i 's/bool_expr_e.BoolUnary/bool_expr_e.Unary/g' */*.py
    sed -r -i 's/bool_expr_e.BoolBinary/bool_expr_e.Binary/g' */*.py
    sed -r -i 's/bool_expr__BoolUnary/bool_expr__Unary/g' */*.py
    sed -r -i 's/bool_expr__BoolBinary/bool_expr__Binary/g' */*.py
  fi

  sed -r -i 's/command.SimpleCommand/command.Simple/g' */*.py
  sed -r -i 's/command_e.SimpleCommand/command_e.Simple/g' */*.py
  sed -r -i 's/command__SimpleCommand/command__Simple/g' */*.py
}

trailing-ws() {
  sed -r -i 's/[ ]+$//g' "$@"
}

#
# OLD STUFF
#

# Hm all of the solutions involve grep --perl or perl itself?
# https://stackoverflow.com/questions/3001177/how-do-i-grep-for-all-non-ascii-characters-in-unix

# Found a latin-1 character in Python-2.7.13/Lib/heapq.py.  Had to add LC_ALL=C.
grep-unicode() {
  LC_ALL=C grep --color='auto' --perl -n '[^\x00-\x7F]'  "$@"
}

find-old-asdl() {
  egrep 'import.*\bruntime\b' */*.py || true
  echo ---

  # Only tests left
  egrep 'import.*\bast\b' */*.py || true
}

# This should be cleaned up
grep-span-funcs() {
  grep MostSpan {osh,core,frontend}/*.py
}

cmd-val() {
  local file=$1
  sed -i 's/arg_vec.strs/cmd_val.argv/g' $file
  sed -i 's/arg_vec.spids/cmd_val.arg_spids/g' $file
  sed -i 's/arg_vector/cmd_value__Argv/g' $file
  sed -i 's/arg_vec/cmd_val/g' $file
}

"$@"
