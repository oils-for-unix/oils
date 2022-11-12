#!/usr/bin/env bash
#
# Abandoned experiment.  Might be useful later.
#
# Usage:
#   devtools/clang-ast.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
source build/common.sh

clang-action() {
  local action=$1
  shift

  log "*** $action"

  # Weird that -ast-list is an argument to -Xclang
  $CLANG_DIR/bin/clang++ -Xclang $action -fsyntax-only "$@"
}

demo() {
  # What's the difference with clang-query and clang-check?
  # CXX=$CLANG_DIR/bin/clang-query

  # These seem useful, but aren't really?
  # -dump-tokens
  # -dump-raw-tokens

  # -fno-color-diagnostics

  # Crashes?
  #CXX="$CLANG_DIR/bin/clang-check -syntax-tree-dump"

  local -a cxx_flags=(
    -std=c++11 -Wall -Wno-invalid-offsetof -D MARK_SWEEP
    -I $PWD  # /home/andy/git/oilshell/oil
  )

  local out_dir=_tmp/clang-ast
  mkdir -p $out_dir

  local src=cpp/leaky_core.cc 
  local out_prefix=$out_dir/$(basename $src)


  # List of function names
  time clang-action -ast-list ${cxx_flags[@]} -c $src > $out_prefix.txt

  # AST text
  time clang-action -ast-dump ${cxx_flags[@]} -c $src > $out_prefix.ast

  # AST json
  time clang-action -ast-dump=json ${cxx_flags[@]} -c $src > $out_prefix.json

  if false; then
    # Tokens go to stderr for some reason
    time clang-action -dump-tokens ${cxx_flags[@]} -c $src 2> $out_prefix.tokens.txt

    time clang-action -dump-raw-tokens ${cxx_flags[@]} -c $src 2> $out_prefix.raw-tokens.txt
  fi

  # Other flags:
  # -ast-dump-filter

  # - 600 KB for list of names
  # - 29M for AST text format
  # - 200M for AST JSON format

  ls -l --si $out_dir

  # 4.3M lines
  wc -l $out_prefix.json
}

filter() {
  # 200 MB of JSON takes 7 seconds
  #time jq '.' < _tmp/foo.json | wc -l

  # hm doesn't show anything, but takes 3 seconds
  time jq 'select(.kind == "FunctionDecl")' < _tmp/foo.json
}

help() {
  #$CLANG_DIR/bin/clang-query --help
  #$CLANG_DIR/bin/clang++ --help

  $CLANG_DIR/bin/clang++ -cc1 --help

  #$CLANG_DIR/bin/clang-check --help
}

"$@"
