#!/usr/bin/env bash
#
# Usage:
#   ./NINJA-config.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/dynamic-deps.sh

asdl-main() { py-tool asdl.asdl_main; }

optview-gen() { py-tool core.optview_gen; }
consts-gen() { py-tool frontend.consts_gen; }
flag-gen() { py-tool frontend.flag_gen; }
lexer-gen() { py-tool frontend.lexer_gen; }
option-gen() { py-tool frontend.option_gen; }
grammar-gen() { py-tool oil_lang.grammar_gen; }
arith-parse-gen() { py-tool osh.arith_parse_gen; }

osh-eval() {
  ### bin/osh_eval is oil-native

  local dir=$DIR/osh_eval
  mkdir -p $dir

  PYTHONPATH=$PY_PATH /usr/bin/env python2 \
    build/dynamic_deps.py py-manifest bin.osh_eval \
  > $dir/all.txt

  set +o errexit
  cat $dir/all.txt | repo-filter | exclude-filter typecheck | mysort \
    > $dir/typecheck.txt

  cat $dir/typecheck.txt | exclude-filter translate | mysort \
    > $dir/translate.txt

  wc -l $dir/*
}

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
  asdl-main

  optview-gen
  consts-gen
  flag-gen
  lexer-gen
  option-gen
  grammar-gen
  arith-parse-gen

  # Explicit dependencies for translating and type checking
  # Baked into mycpp/NINJA.
  osh-eval

  # Pre-baked
  ls -l -d mycpp/NINJA/* pea/NINJA/*

  # Reads the deps.txt files above
  PYTHONPATH=. build/NINJA_main.py
}

main "$@"
