#!/usr/bin/env bash
#
# Calculate and filter deps of Python apps.
#
# Usage:
#   build/dynamic-deps.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

readonly PY_PATH='.:vendor/'

# Temporary
readonly DIR=_build/NINJA

# In git
readonly FILTER_DIR='prebuilt/dynamic-deps'

make-egrep() {
  # match chars until # or space, and line must be non-empty
  gawk '
  match($0, /([^# ]*)/, m) {
    contents = m[0]
    if (contents) {  # skip empty lines
      print(contents)
    }
  }
  '
}

write-filters() {
  ### Write filename filters in the egrep -f format

  # For ./NINJA-config.sh to use.
  # This style lets us add comments.

  # For asdl.asdl_main and other tools
  make-egrep >$FILTER_DIR/filter-py-tool.txt <<'EOF'
__init__.py
typing.py  # vendor/typing.py isn't imported normally
EOF

  # Don't typecheck these files.

  make-egrep >$FILTER_DIR/filter-typecheck.txt <<'EOF'
__init__.py
typing.py

# OrderedDict is polymorphic
pylib/collections_.py

# lots of polymorphic stuff etc.
mycpp/mylib.py

# TODO: move or remove these
tools/deps.py
tools/readlink.py
EOF

  # On top of the typecheck filter, exclude these from translation.  They are
  # not inputs to mycpp.

  make-egrep >$FILTER_DIR/filter-translate.txt <<'EOF'
# generated code shouldn't be translated
_devbuild/
_gen/

# definitions that are used by */*_gen.py
.*_def\.py
.*_spec\.py

asdl/py.*           # pybase.py ported by hand to C++

core/py.*           # pyos.py, pyutil.py ported by hand to C++
core/optview\.py    # core/optview_gen.py

data_lang/py.*      # pyj8.py

frontend/py.*\.py   # py_readline.py ported by hand to C++
frontend/consts.py  # frontend/consts_gen.py
frontend/match.py   # frontend/lexer_gen.py

mycpp/iolib.py       # Implemented in gc_iolib.{h,cC}
mycpp/mops.py       # Implemented in gc_mops.{h,cC}

pgen2/grammar.py    # These files are re-done in C++
pgen2/pnode.py
pgen2/token.py

# should be py_path_stat.py, because it's ported by hand to C++
pylib/path_stat.py

# should be py_bool_stat.py, because it's ported by hand to C++
osh/bool_stat.py
EOF

  wc -l $FILTER_DIR/filter-*
}

repo-filter() {
  ### Select files from the dynamic_deps.py output

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
    build/dynamic_deps.py py-manifest $py_module \
    > $dir/all-pairs.txt

  cat $dir/all-pairs.txt | repo-filter | exclude-filter py-tool | mysort \
    > $dir/deps.txt

  echo "DEPS $dir/deps.txt"
}

# Code generators
list-gen() {
  ls */*_gen.py
}

# mycpp and pea deps are committed to git instead of in _build/NINJA/ because
# users might not have Python 3.10

write-pea() {
  # PYTHONPATH=$PY_PATH 
  local module='pea.pea_main'
  local dir=prebuilt/ninja/$module
  mkdir -p $dir

  source build/dev-shell.sh  # python3

  # Can't use vendor/typing.py
  PYTHONPATH=. python3 \
    build/dynamic_deps.py py-manifest $module \
  > $dir/all-pairs.txt

  cat $dir/all-pairs.txt | repo-filter | mysort | tee $dir/deps.txt

  echo
  echo $dir/*
}

write-mycpp() {
  local module='mycpp.mycpp_main'
  local dir=prebuilt/ninja/$module
  mkdir -p $dir

  if false; then
    ( source $MYCPP_VENV/bin/activate
      PYTHONPATH=$REPO_ROOT:$REPO_ROOT/mycpp:$MYPY_REPO maybe-our-python3 \
        build/dynamic_deps.py py-manifest $module > $dir/all-pairs.txt
    )
  fi

  # TODO: it would be nicer to put this at the top of the file, but we get
  # READONLY errors.
  source build/dev-shell.sh

  python3 build/dynamic_deps.py py-manifest $module > $dir/all-pairs.txt

  local deps=$dir/deps.txt
  cat $dir/all-pairs.txt \
    | grep -v oilshell/oil_DEPS \
    | repo-filter \
    | exclude-filter py-tool \
    | mysort \
    | tee $deps

  # EXTRA FILE
  echo '_bin/datalog/dataflow' >> $deps

  echo
  echo $dir/*
}

mycpp-example-parse() {
  ### Manifests for mycpp/examples/parse are committed to git

  local dir=$DIR/parse
  mkdir -p $dir

  PYTHONPATH=$PY_PATH /usr/bin/env python2 \
    build/dynamic_deps.py py-manifest mycpp.examples.parse \
  > $dir/all-pairs.txt

  local ty=mycpp/examples/parse.typecheck.txt
  local tr=mycpp/examples/parse.translate.txt

  cat $dir/all-pairs.txt | repo-filter | exclude-filter typecheck | mysort > $ty

  cat $ty | exclude-filter translate > $tr

  wc -l $ty $tr

  #head $ty $tr
}

pea-hack() {
  # Leave out help_.py for Soil
  grep -v '_devbuild/gen/help_meta.py' $DIR/bin.oils_for_unix/typecheck.txt \
    > pea/oils-typecheck.txt
}

# Sourced by NINJA-config.sh
if test $(basename $0) = 'dynamic-deps.sh'; then
  "$@"
fi
