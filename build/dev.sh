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

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
readonly REPO_ROOT

source build/common.sh  # for log, $CLANGXX
source soil/deps-apt.sh   # PY3_DEPS
# TODO: We could have the user run soil/deps-apt.sh directly

export PYTHONPATH='.:vendor/'

ubuntu-deps() {
  # python-dev: for all the extension modules
  #   TODO: upgrade Ubuntu and change to python2-dev
  # gawk: used by spec-runner.sh for the special match() function.
  # time: used to collect the exit code and timing of a test
  # libreadline-dev: needed for the build/prepare.sh Python build.
  # cmake: for build/dev.sh yajl-release
  set -x  # show what needs sudo
  sudo apt install \
    python-dev gawk libreadline-dev ninja-build cmake \
    "${PY3_DEPS[@]}"
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

install-py2() {
  set -x

  # pyyaml: for yaml2json
  # typing: because the build/cpython-defs tool
  # flake8: for linting
  # pygments: for doc rendering
  pip install pyyaml typing flake8 pygments

  # not sure why this requires sudo and pip2 doesn't
  # this doesn't work on our code
  # sudo pip3 install flake8
}

install-py3() {
  pip3 install mypy
}

destroy-pip() {
  rm -r -f -v ~/.cache/pip ~/.local/lib/python2.7
}

# 2021-04: I have no idea why I need this on my Xenial machine
# but the Travis continuous build doesn't need it.
install-old-flake8() {
  # Found by bisection and inspection of MY HOME DIR.  It makes the pip
  # dependency resolver "work"...

  pip install 'configparser==4.0.2'
  pip install 'flake8==3.7.9'

  # Test default version
  unset PYTHONPATH
  ~/.local/bin/flake8 --version
}

# Needed for the release process, but not the dev process.
release-ubuntu-deps() {
  # For the release to run test/report.R, you need r-base-core too.
  # cloc is used for line counts
  # valgrind/cachegrind for benchmarks
  sudo apt install r-base-core cloc valgrind
}

# 3/2021: For installing dplyr on Ubuntu Xenial 16.04 LTS, which has an old R version
# Following these instructions
# https://cloud.r-project.org/bin/linux/ubuntu/README.html

# 5/2021: Upgraded to Ubuntu Bionic, which has R 3.4.4.  So it looks like I no
# longer need this.

_install-new-r() {
  # update indices
  apt update -qq

  # install two helper packages we need
  apt install --no-install-recommends software-properties-common dirmngr

  # import the signing key (by Michael Rutter) for these repo
  apt-key adv --keyserver keyserver.ubuntu.com --recv-keys E298A3A825C0D65DFD57CBB651716619E084DAB9

  # add the R 4.0 repo from CRAN -- adjust 'focal' to 'groovy' or 'bionic' as needed
  add-apt-repository 'deb https://cloud.r-project.org/bin/linux/ubuntu xenial-cran40/'

  # Hm I had to run this manually and I got R 4.0
  # 2021-04: Hm this had to be run twice
  apt install --no-install-recommends r-base
}

install-new-r() {
  sudo $0 _install-new-r "$@"
}

# Helper
gen-asdl-py() {
  local asdl_path=$1  # e.g. osh/osh.asdl

  local name
  name=$(basename $asdl_path .asdl)

  local tmp=_tmp/${name}_asdl.py
  local out=_devbuild/gen/${name}_asdl.py

  # abbrev module is optional
  asdl/asdl_main.py mypy "$@" > $tmp

  # BUG: MUST BE DONE ATOMICALLY; otherwise the Python interpreter can
  # import an empty file!
  mv $tmp $out

  echo "$asdl_path -> (asdl_main) -> $out"
}

gen-asdl-cpp() {
  local asdl_path=$1  # e.g. osh/osh.asdl

  local name
  name=$(basename $asdl_path .asdl)

  local out_prefix=${2:-_build/cpp/${name}_asdl}
  local debug_info=_devbuild/gen/${name}_asdl_debug.py

  # abbrev module is optional
  asdl/asdl_main.py cpp $asdl_path $out_prefix $debug_info

  # TODO: expand when .gc is the only thing generated
  #local -a out_files=( $out_prefix* )
  echo "$asdl_path -> (asdl_main) -> $out_prefix* and $debug_info"
}

# TODO: syntax.asdl and runtime.asdl are mutually recursive.
# Do it in one invocation, and use an output dir:
#
# ASDL_PATH=frontend:runtime asdl/asdl_main.py mypy $out_dir ...
#
# It looks like there needs to be a global cache like sys.modules in the ASDL
# compiler.

py-codegen() {
  gen-asdl-py 'asdl/hnode.asdl' --no-pretty-print-methods --py-init-required

  gen-asdl-py frontend/types.asdl
  gen-asdl-py core/runtime.asdl  # depends on syntax.asdl
  gen-asdl-py 'tools/find/find.asdl'

  build/codegen.sh const-mypy-gen  # dependency on bool_arg_type_e
  build/codegen.sh option-mypy-gen
  build/codegen.sh flag-gen-mypy

  # does __import__ of syntax_abbrev.py, which depends on Id.  We could use the
  # AST module later?
  gen-asdl-py frontend/syntax.asdl 'frontend.syntax_abbrev'

  # For tests
  gen-asdl-py 'mycpp/examples/expr.asdl'
}

py-asdl-testdata() {
  gen-asdl-py 'asdl/demo_lib.asdl'  # dependency of typed_demo
  gen-asdl-py 'asdl/typed_demo.asdl'

  gen-asdl-py 'asdl/shared_variant.asdl'
  gen-asdl-py 'asdl/typed_arith.asdl' 'asdl.typed_arith_abbrev'
}

oil-asdl-to-cpp() {
  mkdir -p _build/cpp _devbuild/tmp

  gen-asdl-cpp 'asdl/hnode.asdl' --no-pretty-print-methods

  gen-asdl-cpp frontend/types.asdl  # no dependency on Id
  gen-asdl-cpp core/runtime.asdl
  gen-asdl-cpp frontend/syntax.asdl

  # Problem:
  # - we have both _devbuild/gen/id.h 
  #           and _build/cpp/id_kind_asdl.h
  # - do we want enum class?

  # We also want to generate the lexer here.
  # TranslateOshLexer can have a flag to use different Ids?
  # Instead of id__Eol_Tok, use Id::Eol_Tok.
  # case lex_mode_e::Expr

}

cpp-codegen() {
  build/codegen.sh const-cpp-gen  # dependency on bool_arg_type_e
  build/codegen.sh option-cpp-gen
  build/codegen.sh arith-parse-cpp-gen
  build/codegen.sh flag-gen-cpp
}

oil-cpp-codegen() {
  oil-asdl-to-cpp

  cpp-codegen

  build/native.sh gen-oil-native-sh  # script to build it

  build/translate.sh osh-eval  # translate with mycpp
}

oil-cpp() {
  ./NINJA-config.sh  # Create it for the first time

  oil-cpp-codegen

  time ninja _bin/cxx-dbg/osh_eval
  echo

  wc -l _build/cpp/*
  echo

  ls -l _bin/*/osh_eval*
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

  local arch
  arch=$(uname -m)

  # global opts come first
  $setup_script --quiet build_ext --inplace

  #file $name.so
}

pylibc() {
  rm -f libc.so

  py-ext libc build/setup.py
  native/libc_test.py "$@" > /dev/null
}

fanos() {
  rm -f fanos.so

  py-ext fanos build/setup_fanos.py
  native/fanos_test.py "$@" #> /dev/null
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

  # This causes a lot of spew
  echo 'Running py-yajl unit tests'
  python2 tests/unit.py >/dev/null 2>&1

  # Hm this test doesn't make any assertions.
  zcat test_data/issue_11.gz | python2 tests/issue_11.py >/dev/null
  popd >/dev/null

  # Link it in the repo root
  ln -s -f py-yajl/yajl.so .
}

clean() {
  rm -f --verbose *.so
  rm -r -f --verbose _devbuild

  # These can be stale after renaming things
  build/actions.sh clean-pyc
}

py-source() {
  ### Generate Python source code

  mkdir -p _tmp _devbuild/gen

  # need -r because Python 3 puts a __pycache__ here
  log 'Removing _devbuild/gen/*'
  rm -r -f _devbuild/gen/*

  # So modules are importable.
  touch _devbuild/__init__.py  _devbuild/gen/__init__.py

  py-codegen  # depends on Id

  # Only for testing.
  py-asdl-testdata

  # Needed on Travis.
  oil-grammar
  find-grammar
  demo-grammar  # for mycpp/examples/pgen2_demo
}

# No fastlex, because we don't want to require re2c installation.
py-extensions() {
  pylibc
  line-input
  posix_
  fanos

  # Require submodule
  yajl
}

minimal() {
  py-source
  py-extensions

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

all() {
  rm -f *.so  # 12/2019: to clear old symlinks, maybe get rid of

  py-source
  py-extensions  # no re2c

  # requires re2c: soil/deps-tar.sh layer-re2c
  fastlex
  time-helper
  build/doc.sh all-help
}

if [ $# -eq 0 ]; then
  echo "usage: $0 <function name>"
  exit 1
fi

"$@"
