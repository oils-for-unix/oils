#!/usr/bin/env bash
#
# Set up a development build of Oil on CPython.
# This is in contrast to the release build, which bundles Oil with "OVM" (a
# slight fork of CPython).
#
# Usage:
#   build/dev.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh  # R_PATH

export PYTHONPATH='.:vendor/'

ubuntu-deps() {
  # python-dev: for all the extension modules
  #   TODO: upgrade Ubuntu and change to python2-dev
  # gawk: used by spec-runner.sh for the special match() function.
  # time: used to collect the exit code and timing of a test
  # libreadline-dev: needed for the build/prepare.sh Python build.
  # cmake: for build/dev.sh yajl-release
  set -x  # show what needs sudo
  sudo apt install python-dev gawk libreadline-dev cmake
  set +x

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
  mv $tmp $out

  echo "$asdl_path -> (asdl/tool) -> $out"
}

gen-asdl-cpp() {
  local asdl_path=$1  # e.g. osh/osh.asdl

  local name=$(basename $asdl_path .asdl)

  local out_prefix=${2:-_build/cpp/${name}_asdl}
  local debug_info=_devbuild/gen/${name}_asdl_debug.py

  # abbrev module is optional
  asdl/tool.py cpp $asdl_path $out_prefix $debug_info

  echo "$asdl_path -> $out_prefix and $debug_info"
}

hnode-gc() {
  GC=1 PRETTY_PRINT_METHODS='' gen-asdl-cpp asdl/hnode.asdl _build/cpp/hnode_asdl.gc
}

# TODO: syntax.asdl and runtime.asdl are mutually recursive.
# Do it in one invocation, and use an output dir:
#
# ASDL_PATH=frontend:runtime asdl/tool.py mypy $out_dir ...
#
# It looks like there needs to be a global cache like sys.modules in the ASDL
# compiler.

oil-asdl-to-py() {
  OPTIONAL_FIELDS='' PRETTY_PRINT_METHODS='' gen-asdl-py 'asdl/hnode.asdl'

  gen-asdl-py frontend/types.asdl
  gen-asdl-py core/runtime.asdl  # depends on syntax.asdl
  gen-asdl-py 'tools/find/find.asdl'

  build/codegen.sh const-mypy-gen  # dependency on bool_arg_type_e
  build/codegen.sh option-mypy-gen
  build/codegen.sh flag-gen-mypy

  # does __import__ of syntax_abbrev.py, which depends on Id.  We could use the
  # AST module later?
  gen-asdl-py frontend/syntax.asdl 'frontend.syntax_abbrev'
}

arith-parse-cpp-gen() {
  osh/arith_parse_gen.py > _build/cpp/arith_parse.cc
}

oil-asdl-to-cpp() {
  mkdir -p _build/cpp _devbuild/tmp

  PRETTY_PRINT_METHODS='' gen-asdl-cpp 'asdl/hnode.asdl'

  gen-asdl-cpp frontend/types.asdl  # no dependency on Id

  # Problem:
  # - we have both _devbuild/gen/id.h 
  #           and _build/cpp/id_kind_asdl.h
  # - do we want enum class?

  build/codegen.sh const-cpp-gen  # dependency on bool_arg_type_e
  build/codegen.sh option-cpp-gen

  # We also want to generate the lexer here.
  # TranslateOshLexer can have a flag to use different Ids?
  # Instead of id__Eol_Tok, use Id::Eol_Tok.
  # case lex_mode_e::Expr

  gen-asdl-cpp core/runtime.asdl

  gen-asdl-cpp frontend/syntax.asdl
}

oil-cpp() {
  oil-asdl-to-cpp
  arith-parse-cpp-gen
  build/codegen.sh flag-gen-cpp
  build/mycpp.sh osh-eval  # used to be osh-parse

  echo
  wc -l _build/cpp/*
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

  log ''
  log "$setup_script -> $name.so"

  mkdir -p _devbuild/py-ext
  local arch=$(uname -m)

  # global opts come first
  $setup_script --quiet build_ext --inplace

  #file $name.so
}

pylibc() {
  rm -f libc.so

  py-ext libc build/setup.py
  native/libc_test.py "$@" > /dev/null
}

fastlex() {
  build/codegen.sh ast-id-lex

  # Why do we need this?  It gets stale otherwise.
  rm -f fastlex.so

  py-ext fastlex build/setup_fastlex.py
  native/fastlex_test.py "$@" > /dev/null
}

line-input() {
  # Why do we need this?  It gets stale otherwise.
  rm -f line_input.so

  py-ext line_input build/setup_line_input.py
  native/line_input_test.py "$@" > /dev/null
}

posix_() {
  rm -f posix_.so

  py-ext posix_ build/setup_posix.py
  native/posix_test.py "$@" > /dev/null
}

yajl-unit() {
  pushd py-yajl >/dev/null
  python2 tests/unit.py "$@" > /dev/null
  popd >/dev/null
}

yajl-release() {
  ### Creates a py-yajl/yajl/yajl-2.1.1/ dir, used by build/compile.sh

  pushd py-yajl/yajl >/dev/null
  ./configure
  cmake .
  make

  #ls -l 

  # TODO: Run tests too?  There are run_tests.sh files, but not all of them
  # work.
  popd >/dev/null
}

yajl() {
  ### Build and test yajl binding (depends on submodule)

  log ''
  log "py-yajl/setup.py -> yajl.so"

  pushd py-yajl >/dev/null
  python2 setup.py --quiet build_ext --inplace

  # DISABLED.  It causes a lot of spew.  And yajl will not make it into oil-native.
  # Adapted from py-yajl/runtests.sh
  # python2 tests/unit.py

  # Hm this test doesn't make any assertions.
  zcat test_data/issue_11.gz | python2 tests/issue_11.py >/dev/null
  popd >/dev/null

  # Link it in the repo root
  ln -s -f py-yajl/yajl.so .
}

clean() {
  rm -f --verbose libc.so fastlex.so line_input.so posix_.so
  rm -r -f --verbose _devbuild/py-ext
}

# No fastlex, because we don't want to require re2c installation.
_minimal() {
  mkdir -p _tmp _devbuild/gen

  # need -r because Python 3 puts a __pycache__ here
  log 'Removing _devbuild/gen/*'
  rm -r -f _devbuild/gen/*

  # So modules are importable.
  touch _devbuild/__init__.py  _devbuild/gen/__init__.py

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

  # Require submodule
  yajl
}

minimal() {
  _minimal

  cat <<EOF

*****
'build/dev.sh minimal' succeeded

  It allows you to run and modify Oil quickly, but the lexer will be slow and
  the help builtin won't work.

'build/dev.sh all' requires re2c and libcmark.so.  (Issue #513 is related, ask
on #oil-dev)
*****
EOF
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

time-helper() {
  local out=_devbuild/bin/time-helper
  mkdir -p $(dirname $out)
  cc -std=c99 -o $out benchmarks/time-helper.c
  ls -l $out
}

# Prerequisites: build/codegen.sh {download,install}-re2c
all() {
  rm -f *.so  # 12/2019: to clear old symlinks, maybe get rid of

  _minimal
  fastlex
  time-helper
  build/doc.sh all-help
}

if [ $# -eq 0 ]; then
  echo "usage: $0 <function name>"
  exit 1
fi

"$@"
