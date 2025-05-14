#!/usr/bin/env bash
#
# Creates build.ninja.  Crawls dynamic dependencies.
#
# Usage:
#   ./NINJA-config.sh

set -o nounset
set -o pipefail
set -o errexit

source build/dev-shell.sh  # python2 in $PATH
source build/dynamic-deps.sh  # py-tool, etc

typecheck-translate() {
  local py_module=$1

  local dir=$DIR/$py_module

  mkdir -p $dir

  PYTHONPATH=$PY_PATH /usr/bin/env python2 \
    build/dynamic_deps.py py-manifest "$py_module" \
  > $dir/all.txt

  set +o errexit
  cat $dir/all.txt | repo-filter | exclude-filter typecheck | mysort \
    > $dir/typecheck.txt

  cat $dir/typecheck.txt | exclude-filter translate | mysort \
    > $dir/translate.txt

  echo DEPS $dir/*
}

PY_TOOL=(
  asdl.asdl_main
  core.optview_gen
  frontend.consts_gen
  frontend.flag_gen
  frontend.lexer_gen
  frontend.option_gen
  ysh.grammar_gen
  osh.arith_parse_gen
  frontend.signal_gen
  cpp.embedded_file_gen
)

BIN=(
  bin.hello
  bin.osh_parse
  bin.osh_eval
  bin.oils_for_unix
  yaks.yaks_main  # Experimental IR to C++ translator
)

main() {
  # _build/NINJA/  # Part of the Ninja graph
  #   asdl.asdl_main/
  #     all-pairs.txt
  #     deps.txt
  #   osh_eval/
  #     typecheck.txt
  #     translate.txt

  mkdir -p _build/NINJA

  # Implicit dependencies for tools
  for mod in "${PY_TOOL[@]}"; do
    py-tool $mod
  done

  # Explicit dependencies for translating and type checking
  # Baked into mycpp/NINJA.
  for mod in "${BIN[@]}"; do
    typecheck-translate $mod
  done

  echo DEPS prebuilt/ninja/*/deps.txt
  echo

  # Reads the deps.txt files above
  PYTHONPATH=. build/ninja_main.py
}

main "$@"
