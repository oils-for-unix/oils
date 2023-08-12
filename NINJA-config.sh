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

asdl-main() { py-tool asdl.asdl_main; }

optview-gen() { py-tool core.optview_gen; }
consts-gen() { py-tool frontend.consts_gen; }
flag-gen() { py-tool frontend.flag_gen; }
lexer-gen() { py-tool frontend.lexer_gen; }
option-gen() { py-tool frontend.option_gen; }
grammar-gen() { py-tool ysh.grammar_gen; }
arith-parse-gen() { py-tool osh.arith_parse_gen; }
signal-gen() { py-tool frontend.signal_gen; }
embedded-file-gen() { py-tool cpp.embedded_file_gen; }

osh-eval() {
  ### Old binary

  local dir=$DIR/bin.osh_eval
  mkdir -p $dir

  PYTHONPATH=$PY_PATH /usr/bin/env python2 \
    build/dynamic_deps.py py-manifest bin.osh_eval \
  > $dir/all.txt

  set +o errexit
  cat $dir/all.txt | repo-filter | exclude-filter typecheck | mysort \
    > $dir/typecheck.txt

  cat $dir/typecheck.txt | exclude-filter translate | mysort \
    > $dir/translate.txt

  echo DEPS $dir/*
}

oils-for-unix() {
  ### The main binary

  local dir=$DIR/bin.oils_for_unix
  mkdir -p $dir

  PYTHONPATH=$PY_PATH /usr/bin/env python2 \
    build/dynamic_deps.py py-manifest bin.oils_for_unix \
  > $dir/all.txt

  set +o errexit
  cat $dir/all.txt | repo-filter | exclude-filter typecheck | mysort \
    > $dir/typecheck.txt

  cat $dir/typecheck.txt | exclude-filter translate | mysort \
    > $dir/translate.txt

  echo DEPS $dir/*
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
  signal-gen
  embedded-file-gen

  # Explicit dependencies for translating and type checking
  # Baked into mycpp/NINJA.
  osh-eval
  oils-for-unix

  echo DEPS prebuilt/ninja/*/deps.txt

  echo
  # Special _OIL_DEV for -D GC_TIMING
  _OIL_DEV=1 ./configure

  # Reads the deps.txt files above
  PYTHONPATH=. build/ninja_main.py
}

main "$@"
