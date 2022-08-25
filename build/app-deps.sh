#!/usr/bin/env bash
#
# Calculate and filter deps of Python apps.
#
# Usage:
#   build/app-deps.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source mycpp/common.sh  # $MYPY_REPO

readonly PY_PATH='.:vendor/'

# Temporary
readonly DIR=_build/app-deps

# In git
readonly FILTER_DIR=build/app-deps

write-filters() {
  ### Write files with the egrep -f format

  # We could just manually edit these files in build/app-deps, but they are
  # easier to see here.

  # py-tool filter can be used for Ninja 'depfile' dependencies

  # vendor/typing.py isn't imported normally
  cat >$FILTER_DIR/filter-py-tool.txt <<'EOF'
__init__.py
typing.py
EOF


  # typecheck and translate filters used for EXPLICIT Ninja dependencies --
  # they are inputs to the tool

  # mylib.py causes a bunch of errors
  cat >$FILTER_DIR/filter-typecheck.txt <<'EOF'
__init__.py
typing.py
mycpp/mylib.py
pylib/collections_.py
EOF

  # On top of the typecheck filter, exclude these from translation

  # Note: renaming files to pyoptview, pyconsts.py, pymatch.py, py_path_stat.py
  # etc. would make this filter cleaner.

  cat >$FILTER_DIR/filter-translate.txt <<'EOF'
_devbuild/
.*_def\.py
.*_spec\.py
asdl/py.*
core/py.*
core/optview.py
frontend/consts.py
frontend/match.py
pgen2/parse.py
pylib/path_stat.py
oil_lang/objects.py
osh/bool_stat.py
osh/builtin_process.py
EOF

  wc -l $FILTER_DIR/filter-*
}

repo-filter() {
  ### Select files from the app_deps.py output

  # select what's in the repo; eliminating stdlib stuff
  # eliminate _cache for mycpp running under Python-3.10
  fgrep -v "$REPO_ROOT/_cache" | fgrep "$REPO_ROOT" | awk '{ print $2 }' 
}

exclude-filter() {
  ### Exclude repo-relative paths

  local filter_name=$1

  egrep -v -f $FILTER_DIR/filter-$filter_name.txt
}

mysort() {
  LC_ALL=C sort
}

#
# Programs
#

py-tool() {
  local py_module=$1

  local dir=$DIR/$py_module
  mkdir -p $dir

  PYTHONPATH=$PY_PATH /usr/bin/env python2 \
    build/app_deps.py py-manifest $py_module \
  > $dir/all.txt

  cat $dir/all.txt | repo-filter | exclude-filter py-tool | mysort \
    | tee $dir/repo.txt
}

# Code generators
list-gen() {
  ls */*_gen.py
}

# TODO: precise dependencies for code generation
#
# _bin/py/frontend/consts_gen    # This is a #!/bin/sh stub with a TIMESTAMP
# _bin/py/frontend/consts_gen.d  # dependency file -- when it should be updated
# And then _build/cpp/consts.{cc,h} should have an IMPLICIT dependency on the
# code generator.

asdl-main() { py-tool asdl.asdl_main; }

optview-gen() { py-tool core.optview_gen; }
consts-gen() { py-tool frontend.consts_gen; }
flag-gen() { py-tool frontend.flag_gen; }
lexer-gen() { py-tool frontend.lexer_gen; }
option-gen() { py-tool frontend.option_gen; }
grammar-gen() { py-tool oil_lang.grammar_gen; }
arith-parse-gen() { py-tool osh.arith_parse_gen; }

readonly PY_310=../oil_DEPS/python3

pea() {
  # PYTHONPATH=$PY_PATH 
  local dir=$DIR/pea
  mkdir -p $dir

  # Can't use vendor/typing.py
  PYTHONPATH=. $PY_310 \
    build/app_deps.py py-manifest 'pea.pea_main' \
  > $dir/all.txt

  cat $dir/all.txt | grep -v 'oilshell/oil/_cache/Python' | repo-filter | mysort
}

mycpp() {
  # This is committed to git instead of in _build/app-deps/ because users might
  # not have Python 3.10
  local dir=mycpp/NINJA
  mkdir -p $dir

  local module='mycpp.mycpp_main'

  ( source $MYCPP_VENV/bin/activate
    PYTHONPATH=$REPO_ROOT:$REPO_ROOT/mycpp:$MYPY_REPO maybe-our-python3 \
      build/app_deps.py py-manifest $module > $dir/$module.ALL.txt
  )

  cat $dir/$module.ALL.txt \
    | grep -v oilshell/oil_DEPS \
    | repo-filter \
    | exclude-filter py-tool \
    | mysort \
    | tee $dir/$module.FILTERED.txt
}

# 439 ms to compute all dependencies.
# Should this be done in:
#
# build/dev.sh py-source -- but then you would have to remember
# ./NINJA_config.py -- this makes sense because depfiles are part of the graph
# When each tool is invoked, emulating gcc -M -- then you need a shell wrapper
#   for each tool that calls build/app-deps.sh and has a flag
# build/cpp.sh all?  -- no we want to be demand-driven?

all-py-tool() {
  # Union of all these is IMPLICIT input to build/cpp.sh codegen
  # Plus lexer
  asdl-main

  optview-gen
  consts-gen
  flag-gen
  lexer-gen
  option-gen
  grammar-gen
  arith-parse-gen
}

ninja-config() {
  # TODO:
  # _build/NINJA/  # Part of the Ninja graph
  #   py-tool/
  #     asdl.tool.ALL.txt
  #     asdl.tool.FILTERED.txt
  #     frontend.consts_gen.ALL.txt
  #     frontend.consts_gen.FILTERED.txt
  #   osh_eval/
  #     typecheck.txt
  #     translate.txt
  #
  # Then load *.FILTERED.txt into Ninja

  # Implicit dependencies for tools
  all-py-tool

  # Explicit dependencies for translating and type checking
  osh-eval

  # NOTE: mycpp baked into mycpp/NINJA.

}

mycpp-example-parse() {
  ### Manifests for mycpp/examples/parse are committed to git

  local dir=$DIR/parse
  mkdir -p $dir

  PYTHONPATH=$PY_PATH /usr/bin/env python2 \
    build/app_deps.py py-manifest mycpp.examples.parse \
  > $dir/all.txt

  local ty=mycpp/examples/parse.typecheck.txt
  local tr=mycpp/examples/parse.translate.txt

  cat $dir/all.txt | repo-filter | exclude-filter typecheck | mysort > $ty

  cat $ty | exclude-filter translate > $tr

  wc -l $ty $tr

  #head $ty $tr
}

osh-eval() {
  ### bin/osh_eval is oil-native

  local dir=$DIR/osh_eval
  mkdir -p $dir

  PYTHONPATH=$PY_PATH /usr/bin/env python2 \
    build/app_deps.py py-manifest bin.osh_eval \
  > $dir/all.txt

  set +o errexit
  cat $dir/all.txt | repo-filter | exclude-filter typecheck | mysort \
    > $dir/typecheck.txt

  cat $dir/typecheck.txt | exclude-filter translate | mysort \
    > $dir/translate.txt

  wc -l $dir/*
}

pea-hack() {
  cp -v $DIR/osh_eval/typecheck.txt pea/osh-eval-typecheck.txt
}


# Source by NINJA-config.sh
if test $(basename $0) = 'app-deps.sh'; then
  "$@"
fi
