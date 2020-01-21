#!/bin/bash
#
# Usage:
#   ./typed.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source types/common.sh

deps() {
  set -x
  #pip install typing pyannotate

  # got error with 0.67.0
  #pip3 install 'mypy==0.660'

  # Without --upgrade, it won't install the latest version.
  # In .travis.yaml we apparently install the latest version too (?)
  pip3 install --upgrade 'mypy'
}

# This has a bug
#pyannotate() { ~/.local/bin/pyannotate "$@"; }

readonly PYANN_REPO=~/git/oilshell/pyannotate/

pyann-patched() {
  local tool=$PYANN_REPO/pyannotate_tools/annotations
  export PYTHONPATH=$PYANN_REPO
  # --dump can help
  python $tool "$@"
}

# NOTE: We're testing ASDL code generation with --strict because we might want
# Oil to pass under --strict someday.
typed-demo-asdl() {
  asdl/run.sh gen-typed-demo-asdl
  typecheck --strict \
    _devbuild/gen/typed_demo_asdl.py asdl/typed_demo.py

  PYTHONPATH=. asdl/typed_demo.py "$@"
}

check-arith() {
  # NOTE: There are still some Any types here!  We don't want them for
  # translation.

  local strict='--strict'
  MYPYPATH=. PYTHONPATH=. typecheck $strict \
    asdl/typed_arith_parse.py asdl/typed_arith_parse_test.py asdl/tdop.py
}

typed-arith-asdl() {
  asdl/run.sh gen-typed-arith-asdl
  check-arith

  export PYTHONPATH=. 
  asdl/typed_arith_parse_test.py

  echo '---'
  asdl/typed_arith_parse.py parse '40+2'
  echo

  echo '---'
  asdl/typed_arith_parse.py eval '40+2+5'
  echo
}


readonly MORE_OIL_MANIFEST=types/more-oil-manifest.txt

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
  # `types/osh_parse.sh travis`.
  comm -2 -3 \
    <(checkable-files | sort | grep '.py$' | sed 's@^@./@') \
    <(cat $MORE_OIL_MANIFEST $OSH_PARSE_MANIFEST | sort) \
    | xargs wc -l | sort -n
}

typecheck-files() {
  $0 typecheck --follow-imports=silent $MYPY_FLAGS "$@"
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
  export PYTHONPATH=.
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

typecheck-more-oil() {
  # The --follow-imports=silent option allows adding type annotations
  # in smaller steps without worrying about triggering a bunch of
  # errors from imports.  In the end, we may want to remove it, since
  # everything will be annotated anyway.  (that would require
  # re-adding assert-one-error and its associated cruft, though).
  cat $MORE_OIL_MANIFEST | xargs -- $0 typecheck-files
}

travis() {
  typed-demo-asdl
  # Avoid spew on Travis.
  typed-arith-asdl > /dev/null

  # Ad hoc list of additional files
  typecheck-more-oil
}

# Alias for convenience
check-osh-parse() {
  types/osh-parse.sh check-some
}

collect-types() {
  export PYTHONPATH=".:$PYANN_REPO"
  types/pyann_driver.py "$@"

  ls -l type_info.json
  wc -l type_info.json
}

peek-type-info() {
  grep path type_info.json | sort | uniq -c | sort -n
}

apply-types() {
  local -a files=(frontend/args.py)

  #local -a files=( $(cat _tmp/osh-parse-src.txt | grep -v syntax_asdl.py ) )

  pyann-patched --type-info type_info.json "${files[@]}" "$@"
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

#
# expr_parse demo.  Typecheck it?
#

expr-parse() {
  export PYTHONPATH=.
  echo '1 + 2*3' | bin/expr_parse.py "$@"
}

"$@"
