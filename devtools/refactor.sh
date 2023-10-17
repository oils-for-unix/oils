#!/usr/bin/env bash
#
# Junk drawer for refactoring.  Also see test/lint.sh
#
# Usage:
#   devtools/refactor.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source devtools/run-task.sh  # run-task

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

id-kind() {
  sed --regexp-extended -i 's/import id_kind$/import id_kind_def/' */*.py
  sed --regexp-extended -i 's/id_kind[.]/id_kind_def./g' */*.py
}

import() {
  sed --regexp-extended -i 's/from qsen_ import qsn/from qsn_ import qsn/' */*.py
}

options() {
  #sed -i 's/simple_echo/simple_echo/g' */*.{py,md,sh}

  #sed -i 's/simple_eval_builtin/simple_eval_builtin/g' */*.{py,md,sh}
  #sed -i 's/simple_trap/simple_trap/g' */*.{py,md,sh}

  sed -i 's/parse_backslash/parse_backslash/g' */*.{py,md,sh}
  sed -i 's/parse_backticks/parse_backticks/g' */*.{py,md,sh}
  sed -i 's/parse_dollar/parse_dollar/g' */*.{py,md,sh}
}

rename() {
  cat cpp/cc.txt | while read name; do
    local base=$(basename $name .cc)
    local new=leaky_${base%_leaky}.cc
    echo $name $new

    #sed -i "s/$name/$new/g" */*.{py,sh} || true
    git mv cpp/$name cpp/$new
  done
  return

  cat cpp/h.txt | while read name; do
    local base=$(basename $name .h)
    local new=leaky_${base%_leaky}.h
    echo $name $new

    #sed -i "s/$name/$new/g" */*.{sh,py,cc,h}
    git mv cpp/$name cpp/$new
  done
  return
}

revert() {
  cat cpp/cc.txt | while read name; do
    local new=$(basename $name .cc)_leaky.cc
    echo $name $new

    mv cpp/$new cpp/$name
  done
}

#
# Things we want to get rid of
#

show-usages() {
  local out=$1
  shift
  "$@" | grep -v _test.py | tee $out
  echo
  wc -l $out
}

# 2023-08: 91 left
tval-all() {
  show-usages _tmp/tval-all \
    grep -n -w tval */*.py
}

# 2023-08: 28 left
tval-eval() {
  show-usages _tmp/tval-eval \
    grep -n -w tval */*_eval.py
}

# 2023-08: 72 left
spid-all() {
  show-usages _tmp/spid-all \
    egrep -n 'span_id|spid' */*.py
}

# 2023-08: 4 left
spid-sig() {
  show-usages _tmp/spid-sig \
    egrep -n 'def.*(span_id|spid)' */*.py
}

# 2023-08: 14 usages
no-spid() {
  show-usages _tmp/no-spid \
    egrep -n 'runtime.NO_SPID' */*.py
}

# 69 instances
loc-word() {
  # should NOT wrap CompoundWord
  show-usages _tmp/loc-word \
    fgrep -n 'loc.Word(' */*.py
}

# 2023-08: 155
loc-missing() {
  show-usages _tmp/loc-m \
    egrep -n 'loc.Missing' */*.py
}

mylib-python() {
  show-usages _tmp/py \
    egrep -n 'mylib.PYTHON' */*.py
}

asdl-create() {
  fgrep -n 'CreateNull(alloc' */*.py */*/*.py | egrep -v '_devbuild|_test.py' | tee _tmp/asdl
}

long-sigs() {
   # 32 of these
   egrep --no-filename '^[ ]*# type' */*.py | awk 'length($0) >= 80 { print length($0) $0 }' 
}

long-sigs-where() {

   # jump to the file
   egrep -n '^[ ]*# type' */*.py | awk 'length($0) >= 110 { print }' | tee _tmp/long
}

run-task "$@"
