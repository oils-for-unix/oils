#!/usr/bin/env bash
#
# Source code -> HTML tree
#
# Usage:
#   doctools/src-tree.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd $(dirname $0)/.. && pwd)  # tsv-lib.sh uses this
readonly REPO_ROOT

#source test/common.sh
#source test/tsv-lib.sh

export PYTHONPATH=.

# TODO:
# - should README.md be inserted in index.html ?
#   - probably, sourcehut has this too
#   - use cmark
# - line counts in metrics/source-code.sh could be integrated with this
#   - i.e. we create groups of files there, with subtotals

# Highlighters I'd like to write:
#  - syntax highlighter, that finds string literals and comments
#  - as a side effect it estimates significant lines of code
#    - minus comments and blank lines
#  - supports
#    - Python - multi-line strings
#    - shell and YSH -- here docs?
#    - C++ - #ifdef, including #if 0 perhaps
#    - ASDL can replace line counter in metrics/source-code.sh
#     - it's pretty trivial, since ASDL has no string literals
#    - maybe grammar files

# Columns
# - Name
# - Number of lines
# - Can we get the cloc or sloccount report?
#   - https://github.com/AlDanial/cloc - this is a 17K line Perl script!
#   - https://dwheeler.com/sloccount/ - no release since 2004 ?

lexer-files() {
  ### linked from doc/release-quality.md

  for rel_path in \
    _build/tmp/frontend/match.re2c.txt \
    _gen/frontend/match.re2c.h \
    _gen/frontend/id_kind.asdl_c.h; do
    echo $rel_path
  done
}

_print-files() {
  lexer-files

  # Important stuff
  metrics/source-code.sh overview-list

  # And README.md, etc.
  for f in *.md */*.md doc/*/*.md; do
    echo $f
  done
}

# overview-list has dupes
sorted-files() {
  _print-files | sort | uniq 
}

readonly BASE_DIR=_tmp/src-tree

classify() {
  local prefix=
  sorted-files | while read -r path; do
  case $path in
    *.sh|*.bash|*.ysh)
      echo "$path" >& $shell
      ;;
    *.py|*.pyi|pgen2)  # pgen2 uses Python lexical syntax
      echo "$path" >& $py
      ;;
    *.cc|*.c|*.h)
      echo "$path" >& $cpp
      ;;
    *.R)
      echo "$path" >& $R
      ;;
    *.js)
      echo "$path" >& $js
      ;;
    *.asdl)
      echo "$path" >& $asdl
      ;;
    *.md)
      echo "$path" >& $md
      ;;
    *)
      echo "$path" >& $other
    esac
  done {cpp}>$BASE_DIR/cpp.txt \
       {py}>$BASE_DIR/py.txt \
       {shell}>$BASE_DIR/shell.txt \
       {R}>$BASE_DIR/R.txt \
       {js}>$BASE_DIR/js.txt \
       {md}>$BASE_DIR/md.txt \
       {asdl}>$BASE_DIR/asdl.txt \
       {other}>$BASE_DIR/other.txt

  # Other
  # .mk
  # .re2c.txt
  # configure install
  # .pgen2
  #
  # Just leave those un-highlighted for now

  wc -l $BASE_DIR/*.txt
}

highlight() {
  local variant=opt
  local variant=asan
  doctools/micro-syntax.sh build $variant
  for lang in cpp py; do
    time cat $BASE_DIR/$lang.txt | xargs _tmp/micro-syntax/micro_syntax -l $lang -w \
      | doctools/src_tree.py html-files
  done
}

soil-run() {
  ### Write tree starting at _tmp/src-tree/index.html

  # This will eventually into a .wwz file?  src-tree.wwz?
  # Have to work out the web too
  local out=_tmp/src-tree

  local attrs=_tmp/attrs.txt

  # TODO: Pass to micro-syntax tool
  # Should we pre-determine the file types?
  # i.e. sort them and then pass explicit -lang?

  # py R js
  # cc|c|h   sh|bash   osh|ysh

  time sorted-files | xargs doctools/src_tree.py files $out > $attrs

  time doctools/src_tree.py dirs $out < $attrs
}

cat-benchmark() {
  # 355 ms to cat the files!  It takes 2.75 seconds to syntax highlight 'src_tree.py files'
  #
  # Producing 5.9 MB of text.
  time sorted-files | xargs cat | wc --bytes

  # Note: wc -l is not much slower.
}

micro-bench() {
  # ~435 ms, not bad.  cat is ~355 ms, so that's only 70 ms more.

  local variant=opt
  #local variant=asan
  doctools/micro-syntax.sh build $variant

  # Producing 11.4 MB of text.
  time sorted-files | xargs _tmp/micro-syntax/micro_syntax -l cpp | wc --bytes

  # 18.5 MB of text
  time sorted-files | xargs _tmp/micro-syntax/micro_syntax -l cpp -w | wc --bytes
}


#
# Misc ways of counting files
# TODO: unify or remove these
#

repo() {
  git ls-files
}

no-cpython() {
  grep -v 'Python-2.7.13'
}

compress() {
  local out=_tmp/source-code.zip

  rm -f -v $out

  repo | no-cpython | xargs --verbose -- zip $out
  echo

  # 1688 files in 3.6 MB, OK seems fine
  repo | no-cpython | wc -l

  ls -l -h $out
}

extensions() {
  repo \
    | no-cpython \
    | grep -v 'testdata/' \
    | awk --field-separator . '{ print $(NF) }' \
    | sort | uniq -c | sort -n
}

metrics() {
  metrics/source-code.sh osh-files
  echo
  metrics/source-code.sh ysh-files

  # Also see metrics/line_counts.py (104 lines)
}

line-counts() {
  metrics/source-code.sh overview
  metrics/source-code.sh for-translation
}

lint() {
  # We're not formatting now
  test/lint.sh py2-files-to-format
  echo
  test/lint.sh py3-files
}

if test $(basename $0) = 'src-tree.sh'; then
  "$@"
fi
