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

readonly PY_PATH='.:vendor/'

# Temporary
readonly DIR=_build/app-deps

# In git
readonly FILTER_DIR=build/app-deps

write-filters() {
  ### Write files with the egrep -f format

  # Remove files in the repo or stdlib

  # We could just manually edit these files in build/app-deps, but they are
  # easier to see here.
  # Unfortunately there is no way to put a comment in these files?

  # vendor/typing.py
  cat >$FILTER_DIR/filter-py-tool.txt <<'EOF'
__init__.py
typing.py
EOF

  # mylib.py causes a bunch of errors
  cat >$FILTER_DIR/filter-typecheck.txt <<'EOF'
__init__.py
typing.py
mycpp/mylib.py
pylib/collections_.py
EOF

  # On top of the filters above, exclude these from translation

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
EOF

  wc -l $FILTER_DIR/filter-*
}

repo-filter() {
  ### Select files from the app_deps.py output

  # select what's in the repo; eliminating stdlib stuff
  fgrep "$REPO_ROOT" | awk '{ print $2 }' 
}

exclude-filter() {
  ### Select files based on exclusing relative paths

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

asdl-tool() { py-tool asdl.tool; }

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

source mycpp/common.sh  # $MYPY_REPO

mycpp() {
  local dir=$DIR/parse
  mkdir -p $dir

  # mycpp can't be imported with $PY_310 for some reason
  # typing_extensions?

  ( source $MYCPP_VENV/bin/activate
    PYTHONPATH=$REPO_ROOT:$REPO_ROOT/mycpp:$MYPY_REPO /usr/bin/env python3 \
      build/app_deps.py py-manifest mycpp.mycpp_main > $dir/all.txt
  )

  # TODO: mycpp imports should be 'from mycpp'
  cat $dir/all.txt | grep -v oilshell/oil_DEPS | repo-filter | mysort
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

"$@"
