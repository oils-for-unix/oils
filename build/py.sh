#!/usr/bin/env bash
#
# Build the dev version of Oil on CPython.
# This is in contrast to oils_cpp and the oil.ovm build.
#
# Usage:
#   build/py.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
readonly REPO_ROOT

source build/common.sh  # for log, $CLANGXX
source deps/from-apt.sh   # PY3_DEPS
# TODO: We could have the user run deps/from-apt.sh directly

if test -z "${IN_NIX_SHELL:-}"; then
  source build/dev-shell.sh  # to run 're2c'
fi

export PYTHONPATH='.:vendor/'

ubuntu-deps() {
  # python-dev: for all the extension modules
  #   TODO: upgrade Ubuntu and change to python2-dev
  # gawk: used by spec-runner.sh for the special match() function.
  # time: used to collect the exit code and timing of a test
  # libreadline-dev: needed for the build/prepare.sh Python build.
  # cmake: for build/py.sh yajl-release
  set -x  # show what needs sudo

  # pass -y for say gitpod
  sudo apt "$@" install \
    python-dev gawk libreadline-dev ninja-build cmake \
    "${PY3_DEPS[@]}"
  set +x

  test/spec.sh install-shells-with-apt
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

const-mypy-gen() {
  local out=_devbuild/gen/id_kind_asdl.py
  frontend/consts_gen.py mypy > $out
  log "  (frontend/consts_gen) -> $out"

  out=_devbuild/gen/id_kind.py
  frontend/consts_gen.py py-consts > $out
  log "  (frontend/consts_gen) -> $out"
}

option-mypy-gen() {
  local out=_devbuild/gen/option_asdl.py
  frontend/option_gen.py mypy > $out
  log "  (frontend/option_gen) -> $out"
}

flag-gen-mypy() {
  local out=_devbuild/gen/arg_types.py
  frontend/flag_gen.py mypy > $out
  log "  (frontend/flag_gen) -> $out"
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

  log "$asdl_path -> (asdl_main) -> $out"
}

py-codegen() {
  # note: filename must come first
  gen-asdl-py 'asdl/hnode.asdl' --no-pretty-print-methods --py-init-required

  gen-asdl-py 'frontend/types.asdl'
  gen-asdl-py 'core/runtime.asdl'  # depends on syntax.asdl
  gen-asdl-py 'tools/find/find.asdl'

  const-mypy-gen  # dependency on bool_arg_type_e
  option-mypy-gen
  flag-gen-mypy

  # does __import__ of syntax_abbrev.py, which depends on Id.  We could use the
  # AST module later?
  gen-asdl-py 'frontend/syntax.asdl' 'frontend.syntax_abbrev'

  # For tests
  gen-asdl-py 'mycpp/examples/expr.asdl'
}

py-asdl-examples() {
  gen-asdl-py 'asdl/examples/demo_lib.asdl'  # dependency of typed_demo
  gen-asdl-py 'asdl/examples/typed_demo.asdl'

  gen-asdl-py 'asdl/examples/shared_variant.asdl'
  gen-asdl-py 'asdl/examples/typed_arith.asdl' 'asdl.examples.typed_arith_abbrev'
}

oil-cpp() {
  ### STUB for backward compatibility

  build/cpp.sh all
}

py-ext() {
  ### Build a Python extension

  local name=$1
  local setup_script=$2

  log "  ($setup_script) -> $name.so"

  local arch
  arch=$(uname -m)

  # global opts come first
  $setup_script --quiet build_ext --inplace

  #file $name.so
}

py-ext-test() {
  ### Run a test and log it

  # TODO: Fold this into some kind of Ninja test runner?
  # Or just rely on test/unit.sh all?

  local test_path=$1  # Or a function
  shift

  local log_path=_test/unit/$test_path.log
  mkdir -p $(dirname $log_path)

  set +o errexit
  $test_path "$@" >$log_path 2>&1
  local status=$?
  set -o errexit

  if test $status -eq 0; then
    log "OK $log_path"
  else
    die "FAIL $log_path"
  fi
}

pylibc() {
  rm -f libc.so

  py-ext libc pyext/setup_libc.py
  py-ext-test pyext/libc_test.py "$@"
}

fanos() {
  rm -f fanos.so

  py-ext fanos pyext/setup_fanos.py
  py-ext-test pyext/fanos_test.py "$@"
}

#
# For frontend/match.py
#

lexer-gen() { frontend/lexer_gen.py "$@"; }

print-regex() { lexer-gen print-regex; }
print-all() { lexer-gen print-all; }

# Structure:
#
# _gen
#   frontend/
#     id.asdl_c.h
#     types.asdl_c.h
#     match.re2c.h
# _build/
#   tmp/
#     frontend/
#       match.re2c.in
#     bin/
#       oils_cpp_raw.mycpp.cc

# re2c native.
osh-lex-gen-native() {
  local in=$1
  local out=$2
  # Turn on all warnings and make them native.
  # The COMMENT state can match an empty string at the end of a line, e.g.
  # '#\n'.  So we have to turn that warning off.
  re2c -W -Wno-match-empty-string -Werror -o $out $in
}

fastmatch() {
  local gen_dir=_gen/frontend
  mkdir -p _build/tmp/frontend $gen_dir

  # C version of frontend/types.asdl
  local out=$gen_dir/types.asdl_c.h
  asdl/asdl_main.py c frontend/types.asdl "$@" > $out
  log "  (asdl_main c) -> $out"

  # C version of id_kind
  local out=$gen_dir/id_kind.asdl_c.h
  frontend/consts_gen.py c > $out
  log "  (frontend/consts_gen c) -> $out"

  # Fast matcher
  local tmp=_build/tmp/frontend/match.re2c.txt
  local out=_gen/frontend/match.re2c.h
  lexer-gen c > $tmp
  log "  (lexer_gen) -> $tmp"

  osh-lex-gen-native $tmp $out
  log "$tmp -> (re2c) -> $out"
}

fastlex() {
  fastmatch

  # Why do we need this?  It gets stale otherwise.
  rm -f fastlex.so

  py-ext fastlex pyext/setup_fastlex.py
  py-ext-test pyext/fastlex_test.py
}

line-input() {
  # Why do we need this?  It gets stale otherwise.
  rm -f line_input.so

  py-ext line_input pyext/setup_line_input.py
  py-ext-test pyext/line_input_test.py
}

posix_() {
  rm -f posix_.so

  py-ext posix_ pyext/setup_posix.py
  py-ext-test pyext/posix_test.py
}

yajl-release() {
  ### Creates a py-yajl/yajl/yajl-2.1.1/ dir, used by build/ovm-compile.sh

  pushd py-yajl/yajl >/dev/null
  ./configure
  cmake .
  make

  #ls -l 

  # TODO: Run tests too?  There are run_tests.sh files, but not all of them
  # work.
  popd >/dev/null
}

py-yajl-unit() {
  pushd py-yajl >/dev/null
  python2 tests/unit.py

  echo
  echo 'tests/issue11.py'
  echo

  zcat test_data/issue_11.gz | python2 tests/issue_11.py >/dev/null
  popd >/dev/null
}

yajl() {
  ### Build and test yajl binding (depends on submodule)

  log "  (py-yajl/setup.py) -> yajl.so"

  pushd py-yajl >/dev/null
  python2 setup.py --quiet build_ext --inplace
  popd >/dev/null

  py-ext-test py-yajl-unit

  # Link it in the repo root
  ln -s -f py-yajl/yajl.so .
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
  py-asdl-examples

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
'$0 minimal' succeeded

  It allows you to run and modify Oil quickly, but the lexer will be slow and
  the help builtin won't work.

'$0 all' requires re2c and libcmark.so.  (Issue #513 is related, ask
on #oil-dev)
*****
EOF
}

oil-grammar() {
  mkdir -p _gen/oil_lang
  touch _gen/__init__.py _gen/oil_lang/__init__.py

  oil_lang/grammar_gen.py py oil_lang/grammar.pgen2 _devbuild/gen
}

find-grammar() {
  oil_lang/grammar_gen.py py tools/find/find.pgen2 _devbuild/gen
}

demo-grammar() {
  oil_lang/grammar_gen.py py mycpp/examples/arith.pgen2 _devbuild/gen
}

time-helper() {
  local in=benchmarks/time-helper.c
  local out=_devbuild/bin/time-helper
  mkdir -p $(dirname $out)
  cc -std=c99 -o $out $in
  log "  CC $in"
}

all() {
  rm -f *.so  # 12/2019: to clear old symlinks, maybe get rid of

  py-source
  py-extensions  # no re2c

  # requires re2c: deps/from-tar.sh layer-re2c
  fastlex
  time-helper
  build/doc.sh all-help
}

gitpod-minimal() {
  ubuntu-deps '-y'  # skip prompt
  minimal 
  test/spec.sh smoke

  set -x
  bin/osh -c 'echo hi'
}

if [ $# -eq 0 ]; then
  echo "usage: $0 <function name>"
  exit 1
fi

"$@"
