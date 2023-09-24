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

source build/common.sh  # log

export PYTHONPATH=.

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

  # For some reason it shows py-yajl
  git ls-files | grep -v Python-2.7.13 | grep -v '^py-yajl'
  return

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
    *.cc|*.c|*.h)
      echo "$path" >& $cpp
      ;;
    *.py|*.pyi|*.pgen2)  # pgen2 uses Python lexical syntax
      echo "$path" >& $py
      ;;
    *.sh|*.bash|*.osh|*.ysh|configure|install|uninstall)
      echo "$path" >& $shell
      ;;
    *.asdl)
      echo "$path" >& $asdl
      ;;
    *.R)
      echo "$path" >& $R
      ;;
    *.js)
      echo "$path" >& $js
      ;;
    *.css)
      echo "$path" >& $css
      ;;
    *.md)
      echo "$path" >& $md
      ;;
    *.yml)
      echo "$path" >& $yaml
      ;;
    *.txt)
      echo "$path" >& $txt
      ;;
    *)
      echo "$path" >& $other
    esac
  done {cpp}>$BASE_DIR/cpp.txt \
       {py}>$BASE_DIR/py.txt \
       {shell}>$BASE_DIR/shell.txt \
       {asdl}>$BASE_DIR/asdl.txt \
       {R}>$BASE_DIR/R.txt \
       {js}>$BASE_DIR/js.txt \
       {css}>$BASE_DIR/css.txt \
       {md}>$BASE_DIR/md.txt \
       {yaml}>$BASE_DIR/yaml.txt \
       {txt}>$BASE_DIR/txt.txt \
       {other}>$BASE_DIR/other.txt

  # Other
  # .mk
  # .re2c.txt - rename this one to .h
  #
  # Just leave those un-highlighted for now

  wc -l $BASE_DIR/*.txt
}

all-html-to-files() {
  local out_dir=$1
  for lang in cpp py shell asdl R js md txt other; do
    log "=== $lang ===" 

    cat $BASE_DIR/$lang.txt | xargs _tmp/micro-syntax/micro_syntax -l $lang -w \
      | doctools/src_tree.py write-html-fragments $out_dir
    log ''
  done
}

highlight() {
  local variant=opt
  #local variant=asan
  doctools/micro-syntax.sh build $variant

  local out_dir=$BASE_DIR/www
  mkdir -p $out_dir

  # Figure file types
  classify

  local attrs=$BASE_DIR/attrs.txt

  time all-html-to-files $out_dir > $attrs

  # Now write index.html dir listings
  time doctools/src_tree.py dirs $out_dir < $attrs
}

highlight-old() {
  local attrs=$BASE_DIR/attrs-old.txt

  time sorted-files | xargs doctools/src_tree.py files $out_dir > $attrs

  time doctools/src_tree.py dirs $out_dir < $attrs
}

soil-run() {
  ### Write tree starting at _tmp/src-tree/index.html

  highlight
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

  local lang=cpp

  # Buggy!
  local lang=py

  # optimization:
  # lang=cpp: 11.4 MB -> 11.3 MB
  time sorted-files | xargs _tmp/micro-syntax/micro_syntax -l $lang | wc --bytes

  # optimization:
  # lang=cpp: 18.5 MB -> 18.4 MB
  time sorted-files | xargs _tmp/micro-syntax/micro_syntax -l $lang -w | wc --bytes
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
