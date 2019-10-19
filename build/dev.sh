#!/usr/bin/env bash
#
# Set up a development build of Oil on CPython.
# This is in constrast to the release build, which bundles Oil with "OVM" (a
# slight fork of CPython).

# Build Python extension modules.  We use symlinks instead of installing them
# globally (or using virtualenv).
#
# Usage:
#   ./pybuild.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh  # R_PATH

export PYTHONPATH='.:vendor/'

ubuntu-deps() {
  # python-dev: for pylibc
  # gawk: used by spec-runner.sh for the special match() function.
  # time: used to collect the exit code and timing of a test
  # libreadline-dev: needed for the build/prepare.sh Python build.
  sudo apt install python-dev gawk time libreadline-dev

  test/spec.sh install-shells
}

# This is what Python uses on OS X.
#
# https://www.thrysoee.dk/editline/
install-libedit() {
  sudo apt install libedit-dev
}

libedit-flags() {
  pkg-config --libs --cflags libedit
}

# Needed for the release process, but not the dev process.
release-ubuntu-deps() {
  # For the release to run test/report.R, you need r-base-core too.
  # cloc is used for line counts
  # TODO: switch to CommonMark rather than using markdown.pl.
  sudo apt install r-base-core cloc markdown
}

r-packages() {
  # Install to a directory that doesn't require root.  This requires setting
  # R_LIBS_USER.  Or library(dplyr, lib.loc = "~/R", but the former is preferable.
  mkdir -p ~/R
  INSTALL_DEST=$R_PATH Rscript -e 'install.packages(c("dplyr", "tidyr", "stringr"), lib=Sys.getenv("INSTALL_DEST"), repos="http://cran.us.r-project.org")'
}

test-r-packages() {
  R_LIBS_USER=$R_PATH Rscript -e 'library(dplyr)'
}

# Produces _devbuild/gen/osh_help.py
gen-help() {
  build/doc.sh osh-quick-ref
}

# Helper
gen-asdl-py() {
  local asdl_path=$1  # e.g. osh/osh.asdl

  local name=$(basename $asdl_path .asdl)

  local tmp=_tmp/${name}_asdl.py
  local out=_devbuild/gen/${name}_asdl.py

  # abbrev module is optional
  asdl/tool.py mypy "$@" > $tmp

  # BUG: MUST BE DONE ATOMICALLY ATOMIC; otherwise the Python interpreter can
  # import an empty file!
  mv -v $tmp $out

  echo "Wrote $out"
}

gen-asdl-cpp() {
  local asdl_path=$1  # e.g. osh/osh.asdl

  local name=$(basename $asdl_path .asdl)

  local out_prefix=_devbuild/gen-cpp/${name}_asdl

  # abbrev module is optional
  asdl/tool.py cpp $asdl_path $out_prefix

  echo "Wrote $out_prefix"
}

# TODO: syntax.asdl and runtime.asdl are mutually recursive.
# Do it in one invocation, and use an output dir:
#
# ASDL_PATH=frontend:runtime asdl/tool.py mypy $out_dir ...
#
# It looks like there needs to be a global cache like sys.modules in the ASDL
# compiler.

oil-asdl-to-py() {
  PRETTY_PRINT_METHODS='' gen-asdl-py 'asdl/hnode.asdl'

  gen-asdl-py frontend/types.asdl  # no dependency on Id

  build/codegen.sh id-mypy-gen  # dependency on bool_arg_type_e

  gen-asdl-py frontend/syntax.asdl 'frontend.syntax_abbrev'
  gen-asdl-py osh/runtime.asdl
  gen-asdl-py 'tools/find/find.asdl'
}

oil-asdl-to-cpp() {
  local dir='_devbuild/gen-cpp'
  mkdir -p $dir

  PRETTY_PRINT_METHODS='' gen-asdl-cpp 'asdl/hnode.asdl'

  gen-asdl-cpp frontend/types.asdl  # no dependency on Id

  # Problem:
  # - we have both _devbuild/gen/id.h 
  #           and _devbuild/gen-cpp/id_kind_asdl.h
  # - do we want enum class?

  build/codegen.sh id-cpp-gen  # dependency on bool_arg_type_e

  # We also want to generate the lexer here.
  # TranslateOshLexer can have a flag to use different Ids?
  # Instead of id__Eol_Tok, use Id::Eol_Tok.
  # case lex_mode_e::Expr

  gen-asdl-cpp frontend/syntax.asdl
  gen-asdl-cpp osh/runtime.asdl

  echo
  wc -l $dir/*
}

# TODO: should fastlex.c be part of the dev build?  It means you need re2c
# installed?  I don't think it makes sense to have 3 builds, so yes I think we
# can put it here for simplicity.
# However one problem is that if the Python lexer definition is changed, then
# you need to run re2c again!  I guess you should just provide a script to
# download it.

py-ext() {
  local name=$1
  local setup_script=$2

  mkdir -p _devbuild/py-ext
  local arch=$(uname -m)
  $setup_script build --build-lib _devbuild/py-ext/$arch

  shopt -s failglob
  local so=$(echo _devbuild/py-ext/$arch/$name.so)
  ln -s -f -v $so $name.so

  file $name.so
}

pylibc() {
  py-ext libc build/setup.py
  native/libc_test.py "$@" > /dev/null
}

fastlex() {
  build/codegen.sh ast-id-lex

  # Why do we need this?  It gets stale otherwise.
  rm -f _devbuild/py-ext/x86_64/fastlex.so

  py-ext fastlex build/setup_fastlex.py
  native/fastlex_test.py "$@" > /dev/null
}

line-input() {
  # Why do we need this?  It gets stale otherwise.
  rm -f _devbuild/py-ext/x86_64/line_input.so

  py-ext line_input build/setup_line_input.py
  native/line_input_test.py "$@" > /dev/null
}

posix_() {
  rm -f _devbuild/py-ext/x86_64/posix_.so

  py-ext posix_ build/setup_posix.py
  native/posix_test.py "$@" > /dev/null
}

clean() {
  rm -f --verbose libc.so fastlex.so line_input.so posix_.so
  rm -r -f --verbose _devbuild/py-ext
}

# No fastlex, because we don't want to require re2c installation.
minimal() {
  mkdir -p _tmp _devbuild/gen

  # need -r because Python 3 puts a __pycache__ here
  rm -v -r -f _devbuild/gen/*

  # So modules are importable.
  touch _devbuild/__init__.py  _devbuild/gen/__init__.py

  gen-help

  oil-asdl-to-py  # depends on Id

  # Only for testing.
  asdl/run.sh gen-typed-demo-asdl
  asdl/run.sh gen-typed-arith-asdl
  asdl/run.sh gen-shared-variant-asdl

  # Needed on Travis.
  oil-grammar
  find-grammar

  pylibc
  line-input
  posix_
}

oil-grammar() {
  oil_lang/grammar_gen.py marshal oil_lang/grammar.pgen2 _devbuild/gen
}

find-grammar() {
  oil_lang/grammar_gen.py marshal tools/find/find.pgen2 _devbuild/gen
}

demo-grammar() {
  oil_lang/grammar_gen.py marshal mycpp/examples/arith.pgen2 _devbuild/gen
}

# Prerequisites: build/codegen.sh {download,install}-re2c
all() {
  minimal
  fastlex
}

if [ $# -eq 0 ]; then
  echo "usage: $0 <function name>"
  exit 1
fi

"$@"
