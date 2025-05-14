#!/usr/bin/env bash
#
# Calculate and filter deps of Python apps.
#
# Usage:
#   build/dynamic-deps.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# Note on the cd option, "-P": Resolve symlinks in the current working
# directory.  This is needed to make `grep $REPO_ROOT...` in `repo-filter
# (build/dynamic-deps.sh)` work.  Later, `repo-filter` and related parts may be
# rewritten using AWK to handle it better.
REPO_ROOT=$(cd -P "$(dirname $0)/.."; pwd)

readonly PY_PATH='.:vendor/'

# Temporary
readonly DIR=_build/NINJA

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
  make-egrep >build/default.deps-filter.txt <<'EOF'
__init__.py
typing.py  # vendor/typing.py isn't imported normally
EOF

  #
  # DEFAULT typecheck and translate filter
  #
  make-egrep >build/default.typecheck-filter.txt <<'EOF'
__init__.py
typing.py

# OrderedDict is polymorphic
pylib/collections_.py

# lots of polymorphic stuff etc.
mycpp/mylib.py
EOF

  make-egrep >build/default.translate-filter.txt <<'EOF'
# generated code shouldn't be translated
_devbuild/
_gen/

asdl/py.*           # pybase.py ported by hand to C++

mycpp/iolib.py      # Implemented in gc_iolib.{h,cC}
mycpp/mops.py       # Implemented in gc_mops.{h,cC}
EOF

  #
  # OILS typecheck and translate filter
  #
  make-egrep >bin/oils_for_unix.typecheck-filter.txt <<'EOF'
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

  make-egrep >bin/oils_for_unix.translate-filter.txt <<'EOF'
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

mycpp/iolib.py      # Implemented in gc_iolib.{h,cC}
mycpp/mops.py       # Implemented in gc_mops.{h,cC}

pgen2/grammar.py    # These files are re-done in C++
pgen2/pnode.py
pgen2/token.py

# should be py_path_stat.py, because it's ported by hand to C++
pylib/path_stat.py

# should be py_bool_stat.py, because it's ported by hand to C++
osh/bool_stat.py
EOF

  wc -l */*.*-filter.txt
}

repo-filter() {
  ### Select files from the dynamic_deps.py output

  # select what's in the repo; eliminating stdlib stuff
  # eliminate _cache for mycpp running under Python-3.10
  grep -F -v "$REPO_ROOT/_cache" | grep -F "$REPO_ROOT" | awk '{ print $2 }' 
}

exclude-files() {
  local filter_file=$1
  grep -E -v -f $filter_file
}

mysort() {
  LC_ALL=C sort
}

# Code generators
list-gen() {
  ls */*_gen.py
}

#
# Invocations of dynamic_deps
#

py2-manifest() {
  local py_module=$1
  local dir=$2
  PYTHONPATH=$PY_PATH /usr/bin/env python2 \
    build/dynamic_deps.py py-manifest $py_module \
    > $dir/all-pairs.txt
}

py3-manifest() {
  local dir=$1
  python3 build/dynamic_deps.py py-manifest $module > $dir/all-pairs.txt
}

py-tool() {
  local py_module=$1

  local dir=$DIR/$py_module
  mkdir -p $dir

  py2-manifest $py_module $dir

  cat $dir/all-pairs.txt | repo-filter | exclude-files build/default.deps-filter.txt | mysort \
    > $dir/deps.txt

  echo "DEPS $dir/deps.txt"
}

typecheck-translate() {
  local py_module=$1
  local typecheck_filter=${2:-}
  local translate_filter=${3:-}

  local py_rel_path=${py_module//'.'/'/'}
  if test -z "$typecheck_filter"; then
    local custom="$py_rel_path.typecheck-filter.txt"
    if test -f "$custom"; then
      typecheck_filter=$custom
    else
      typecheck_filter=build/default.typecheck-filter.txt
    fi
  fi

  if test -z "$translate_filter"; then
    local custom="$py_rel_path.translate-filter.txt"
    if test -f "$custom"; then
      translate_filter=$custom
    else
      translate_filter=build/default.translate-filter.txt
    fi
  fi

  if false; then
    echo "  | PY        $py_module"
    echo "  | TYPECHECK $typecheck_filter"
    echo "  | TRANSLATE $translate_filter"
  fi

  local dir=$DIR/$py_module

  mkdir -p $dir

  py2-manifest $py_module $dir

  set +o errexit
  cat $dir/all-pairs.txt | repo-filter | exclude-files $typecheck_filter | mysort \
    > $dir/typecheck.txt

  cat $dir/typecheck.txt | exclude-files $translate_filter | mysort \
    > $dir/translate.txt

  echo DEPS $dir/*
}

# mycpp and pea deps are committed to git instead of in _build/NINJA/ because
# users might not have Python 3.10

write-pea() {
  local module='pea.pea_main'
  local dir=prebuilt/ninja/$module
  mkdir -p $dir

  source build/dev-shell.sh  # python3

  # Can't use vendor/typing.py
  py3-manifest $dir

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

  py3-manifest $dir

  local deps=$dir/deps.txt
  cat $dir/all-pairs.txt \
    | grep -v oilshell/oil_DEPS \
    | repo-filter \
    | exclude-files build/default.deps-filter.txt \
    | mysort \
    | tee $deps

  echo
  echo $dir/*
}

mycpp-example-parse() {
  ### Manifests for mycpp/examples/parse are committed to git

  local dir=$DIR/parse
  mkdir -p $dir

  py2-manifest mycpp.examples.parse $dir

  local ty=mycpp/examples/parse.typecheck.txt
  local tr=mycpp/examples/parse.translate.txt

  # TODO: remove oils-for-unix
  cat $dir/all-pairs.txt | repo-filter |
    exclude-files build/default.typecheck-filter.txt | mysort > $ty

  cat $ty | exclude-files build/default.translate-filter.txt > $tr

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
