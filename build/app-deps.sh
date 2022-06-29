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

  # We could just manually edit test files in build/app-deps, but they are
  # easier to see here.
  # Unfortunately there is no way to put a comment in these files?

  cat >$FILTER_DIR/filter-mycpp-example.txt <<'EOF'
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

filter() {
  ### Select files from the app_deps.py output

  local filter_name=$1

  # select what's in the repo; eliminating stdlib stuff
  fgrep "$REPO_ROOT" \
    | awk '{ print $2 }' \
    | egrep -v -f $FILTER_DIR/filter-$filter_name.txt \
    | LC_ALL=C sort
}

#
# Programs
#

asdl() {
  ### Use ASDL as a demo; we don't need it

  local dir=$DIR/asdl
  mkdir -p $dir

  PYTHONPATH=$PY_PATH /usr/bin/env python2 \
    build/app_deps.py py-manifest asdl.tool \
  > $dir/all.txt

  cat $dir/all.txt | filter mycpp-example | tee $dir/repo.txt
}

mycpp() {
  ### mycpp can't be crawled because mycpp has Python 3 type syntax

  PYTHONPATH=$PY_PATH /usr/bin/env python2 \
    build/app_deps.py py-manifest mycpp.mycpp_main
}

mycpp-example-parse() {
  ### mycpp/examples/parse

  local dir=$DIR/parse
  mkdir -p $dir

  PYTHONPATH=$PY_PATH /usr/bin/env python2 \
    build/app_deps.py py-manifest mycpp.examples.parse  \
  > $dir/all.txt

  cat $dir/all.txt | filter mycpp-example | tee $dir/repo.txt
}

osh-eval() {
  ### bin/osh_eval is oil-native

  local dir=$DIR/osh_eval
  mkdir -p $dir

  PYTHONPATH=$PY_PATH /usr/bin/env python2 \
    build/app_deps.py py-manifest bin.osh_eval \
  > $dir/all.txt

  set +o errexit
  cat $dir/all.txt | filter typecheck > $dir/typecheck.txt

  cat $dir/typecheck.txt | egrep -v -f $FILTER_DIR/filter-translate.txt > $dir/translate.txt

  wc -l $dir/*
}

"$@"
