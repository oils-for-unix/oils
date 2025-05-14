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

osh-parse() {
  ### Test binary
  typecheck-translate bin.osh_parse
}

osh-eval() {
  ### Test binary
  typecheck-translate bin.osh_eval
}

oils-for-unix() {
  ### The main binary
  typecheck-translate bin.oils_for_unix
}

# TODO: Prune deps
# j8.py depends on vm.HeapValueId() for cycle detection
# But that's in the JSON8 PRINTER, which yaks doesn't need
# vm.py depends on cmd_eval.py and a whole bunch of other stuff
#
# Well I guess you can create a cycle in nil8, especially if we have <- and so
# forth.
#
# So that function should go in another file.

yaks() {
  ### Experimental IR to C++ translator
  typecheck-translate yaks.yaks_main
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
  osh-parse
  osh-eval
  oils-for-unix
  yaks

  echo DEPS prebuilt/ninja/*/deps.txt
  echo

  # Reads the deps.txt files above
  PYTHONPATH=. build/ninja_main.py
}

main "$@"
