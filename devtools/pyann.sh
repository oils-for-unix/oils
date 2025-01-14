#!/usr/bin/env bash
#
# Usage:
#   types/run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source devtools/common.sh

readonly PY_PATH='.:vendor/'  # note: could consolidate with other scripts

deps() {
  set -x
  #pip install typing pyannotate

  # got error with 0.67.0
  #pip3 install 'mypy==0.660'

  # Without --upgrade, it won't install the latest version.
  # In .travis.yaml we apparently install the latest version too (?)
  pip3 install --user --upgrade 'mypy'
}

checkable-files() {
  # syntax_abbrev.py is "included" in _devbuild/gen/syntax_asdl.py; it's not a standalone module
  metrics/source-code.sh osh-files | grep -v syntax_abbrev.py
  metrics/source-code.sh oil-lang-files
}

need-typechecking() {
  # This command is useful to find files to annotate and add to
  # $MORE_OIL_MANIFEST.
  # It shows all the files that are not included in
  # $MORE_OIL_MANIFEST or $OSH_PARSE_MANIFEST, and thus are not yet
  # typechecked by typecheck-more-oil here or
  # `types/oil-slice.sh soil-run`.

  build/dynamic-deps.sh osh-eval
  echo

  comm -2 -3 \
    <(checkable-files | sort | grep '.py$') \
    <({ more-oil-manifest; cat _build/NINJA/osh_eval/typecheck.txt; } | sort) \
    | xargs wc -l | sort -n
}

readonly -a COMMON_TYPE_MODULES=(_devbuild/gen/runtime_asdl.py _devbuild/gen/syntax_asdl.py)

add-imports() {
  # Temporary helper to add missing class imports to the 'if
  # TYPE_CHECKING:' block of a single module, if the relevant
  # classes are found in one of COMMON_TYPE_MODULES

  # Also, this saves the typechecking output to the file named by
  # $typecheck_out, to make it possible to avoid having to run two
  # redundant (and slow) typechecking commands.  You can just cat that
  # file after running this function.
  local module=$1
  export PYTHONPATH=$PY_PATH
  readonly module_tmp=_tmp/add-imports-module.tmp
  readonly typecheck_out=_tmp/add-imports-typecheck-output
  set +o pipefail
  # unbuffer is just to preserve colorization (it tricks the command
  # into thinking it's writing to a pty instead of a pipe)
  unbuffer types/run.sh typecheck-files "$module" | tee "$typecheck_out" | \
    grep 'Name.*is not defined' | sed -r 's/.*'\''(\w+)'\''.*/\1/' | \
    sort -u | python devtools/findclassdefs.py "${COMMON_TYPE_MODULES[@]}" | \
    xargs python devtools/typeimports.py "$module" > "$module_tmp"
  set -o pipefail

  if ! diff -q "$module_tmp" "$module" > /dev/null
  then
    cp $module "_tmp/add-imports.$(basename $module).bak"
    mv "$module_tmp" "$module"
	echo "Updated $module"
  fi
}

#
# PyAnnotate
#

# This has a bug
#pyannotate() { ~/.local/bin/pyannotate "$@"; }

readonly PYANN_REPO=~/git/oils-for-unix/pyannotate/

VENV=_tmp/pyann-venv

make-venv() {
  python3 -m venv $VENV
}

install-deps() {
  . $VENV/bin/activate
  python3 -m pip install -r $PYANN_REPO/requirements.txt
}

pyann-patched() {
  . $VENV/bin/activate
  local tool=$PYANN_REPO/pyannotate_tools/annotations
  #export PYTHONPATH=$PYANN_REPO:vendor

  # --dump can help
  python3 $tool "$@"
}


#
# Second try
#

VENV2=_tmp/pyann-venv2

make-venv2() {
  python3 -m venv $VENV2
}

install2() {
  . $VENV2/bin/activate
  python3 -m pip install pyannotate
}

tool-demo2() {
  . $VENV2/bin/activate
  python3 -m pyannotate_tools.annotations
}

lib-demo2() {
  . $VENV2/bin/activate
  #echo $PYTHONPATH

  # DOES NOT WORK - this is Python 2 code!!!
  python3 devtools/pyann_driver.py "$@"

  ls -l type_info.json
  wc -l type_info.json
}

#
# Third try - the problem is python2
#

deps3() {
  # Gah my custom python2 build doesn't have pip or venv!
  python2 -m pip install -r $PYANN_REPO/requirements.txt
}

# September 2019
PYANN_URL='https://files.pythonhosted.org/packages/0d/26/2f68c02fae0b88d9cefdbc632edad190d61621b5660c72c920be1e52631e/pyannotate-1.2.0.tar.gz'

# October 2019
MYPY_EXT_URL='https://files.pythonhosted.org/packages/63/60/0582ce2eaced55f65a4406fc97beba256de4b7a95a0034c6576458c6519f/mypy_extensions-0.4.3.tar.gz'

# December 2024
SIX_URL='https://files.pythonhosted.org/packages/94/e7/b2c673351809dca68a0e064b6af791aa332cf192da575fd474ed7d6f16a2/six-1.17.0.tar.gz'

download-tarballs() {
  wget --no-clobber --directory _tmp \
    $PYANN_URL $MYPY_EXT_URL $SIX_URL
}

PY_PATH_2='.:vendor:_tmp/pyannotate-1.2.0:_tmp/mypy_extensions-0.4.3:_tmp/six-1.17.0'

collect-types() {
  # syntax error?
  # Now it requires python3
  # I think we need an old release
  # https://pypi.org/project/mypy-extensions/
  # https://github.com/python/mypy_extensions
  # TypedDict
  # https://github.com/python/mypy_extensions/commit/e0c6670e05a87507d59b7d3a0aa2eec88e9813b0

  #local ext=~/git/oils-for-unix/mypy_extensions
  #export PYTHONPATH=".:$PYANN_REPO:$ext"

  PYTHONPATH=$PY_PATH_2 devtools/pyann_driver.py "$@"

  ls -l type_info.json
  wc -l type_info.json
}

osh-pyann() {
  export PYTHONPATH=".:$PYANN_REPO"
  PYANN_OUT='a1.json' bin/oil.py osh "$@"
}

pyann-demo() {
  rm -f -v *.json
  osh-pyann -c 'pushd /; echo hi; popd'
  ls -l *.json
}

pyann-interactive() {
  osh-pyann --rcfile /dev/null "$@"
}

pyann-spec-demo() {
  local dir=_tmp/pyann-spec
  mkdir -p $dir
  export OSH_LIST=bin/osh-pyann
  test/spec.sh assign --pyann-out-dir $dir "$@"

  ls -l $dir
}

peek-type-info() {
  grep path type_info.json | sort | uniq -c | sort -n
}

apply-types() {
  local json=${1:-type_info.json}
  shift
  #local -a files=(osh/builtin_comp.py core/completion.py)
  local -a files=(lazylex/*.py doctools/*.py)

  #local -a files=( $(cat _tmp/osh-parse-src.txt | grep -v syntax_asdl.py ) )

  # Use -w to write files
  set -x
  PYTHONPATH=$PY_PATH_2 \
    python2 -m pyannotate_tools.annotations --type-info $json "${files[@]}" "$@"

  #pyann-patched --type-info $json "${files[@]}" "$@"
}

apply-many() {
  for j in _tmp/pyann-spec/*.json; do
    apply-types $j -w
  done
}

sub() {
  local f=$1
  types/refactor.py sub < $f > _tmp/sub.txt
  diff -u _tmp/sub.txt $f
}

audit-hacks() {
  # I used a trailing _ in a couple places to indicates hacks
  # A MyPy upgrade might fix this?
  #egrep -n --context 1 '[a-z]+_ ' osh/*_parse.py

  # spids on base class issue
  egrep --color -n --context 1 '_temp' osh/*_parse.py

  echo ---

  # a few casts because Id ; is TokenWord.
  egrep --color -w 'cast' {osh,core,frontend}/*.py

  echo ---

  egrep --color -w 'type: ignore' {osh,core,frontend}/*.py
}

"$@"
