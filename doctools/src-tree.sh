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

install-deps() {
  sudo apt-get install moreutils  # for isutf8
}

lexer-files() {
  ### linked from doc/release-quality.md

  for rel_path in \
    _gen/_tmp/match.re2c-input.h \
    _gen/frontend/match.re2c.h \
    _gen/frontend/id_kind.asdl_c.h; do
    echo $rel_path
  done
}

_print-files() {
  #lexer-files

  find _gen/ -type f

  # TODO: move _devbuild/bin/time-helper elsewhere?
  find _devbuild/ -type f -a -name '*.py'
  find _devbuild/help -type f

  # For some reason it shows py-yajl
  # Remove binary file (probably should delete it altogether, but it's a nice
  # test of UTF-8)

  git ls-files | egrep -v 'Python-2.7.13|^py-yajl|rsa_travis.enc' 

  return

  # We also had this way of categorizing.  Should unify these line counts with
  # micro-syntax.
  metrics/source-code.sh overview-list
}

# overview-list has dupes
sorted-files() {
  _print-files | sort | uniq 
}

readonly BASE_DIR=_tmp/src-tree

classify() {
  ### Classify files on stdin

  while read -r path; do
    case $path in
      */here-doc.test.sh|*/posix.test.sh|*/gold/complex-here-docs.sh|*/07-unterminated-here-doc.sh)
        # Plain text since they can have invalid here docs
        #
        # TODO: make a style for *.test.sh?
        echo "$path" >& $txt
        ;;
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
  for lang in cpp py shell asdl R js css md yaml txt other; do
    log "=== $lang ===" 

    cat $BASE_DIR/$lang.txt | xargs _tmp/micro-syntax/micro_syntax -l $lang -w \
      | doctools/src_tree.py write-html-fragments $out_dir
    log ''
  done
}

check-is-utf8() {
  local manifest=$1

  log '--- Checking that files are UTF-8'
  log ''

  if ! xargs isutf8 --list < $manifest; then
    echo
    die "The files shown aren't UTF-8"
  fi
}

highlight() {
  local variant=opt
  #local variant=asan

  doctools/micro-syntax.sh build $variant
  echo

  local out_dir=$BASE_DIR/www
  mkdir -p $out_dir

  sorted-files > $BASE_DIR/manifest.txt
  wc -l $BASE_DIR/manifest.txt
  echo

  # Fails if there is non UTF-8
  # Disable until moreutils is in our Soil CI images
  # check-is-utf8 $BASE_DIR/manifest.txt

  # Figure file types
  classify < $BASE_DIR/manifest.txt

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

if test $(basename $0) = 'src-tree.sh'; then
  "$@"
fi
