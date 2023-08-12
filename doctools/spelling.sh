#!/usr/bin/env bash
#
# Spell checker.
#
# Usage:
#   doctools/spelling.sh <function name>
#
# Examples:
#   doctools/spelling.sh check-oil-docs
#   doctools/spelling.sh check-blog

set -o nounset
set -o pipefail
set -o errexit

# Make this symlink work:
#   ~/git/oilshell/oilshell.org -> ../oil/doctools/spelling.sh

# This file is doctools/spelling.sh
OIL_ROOT=$(dirname $(dirname $(readlink -f $0)))
readonly OIL_ROOT
echo $OIL_ROOT

readonly SPELLING_PY=$OIL_ROOT/doctools/spelling.py
readonly BASE_DIR=_tmp/spelling  # relative path

spelling() {
  PYTHONPATH=$OIL_ROOT $SPELLING_PY "$@"
}

to-ninja() {
  echo '
rule text-dump
  command = lynx -dump $in > $out
  description = text-dump $in $out

rule word-split
  command = cat $in | PYTHONPATH='"$OIL_ROOT $SPELLING_PY"' word-split > $out
  description = word-split $in $out

'

  while read html; do
    # replace .html with .txt
    local txt=$BASE_DIR/${html//'.html'/.txt}
    local words=$BASE_DIR/${html//'.html'/.words}

    echo "build $txt: text-dump $html"
    echo
    echo "build $words: word-split $txt"
    echo
  done
}

lines() {
  for x in "$@"; do
    echo "$x"
  done
}

doc-to-text() {
  ### Convert files in the given directories

  # for the blog, omit anything that starts with _
  lines "$@" | to-ninja > _tmp/doc.ninja

  ninja -f _tmp/doc.ninja
}

clean() {
  rm -r -f -v $BASE_DIR
}

check-tree() {
  local subdir=$1
  shift

  # Depends on build/doc.sh all-markdown
  doc-to-text "$@"

  echo
  echo 'Word Counts'
  echo

  # For curiosity: word count by file
  find $BASE_DIR/$subdir -name '*.words' | xargs wc -l | sort -n

  # Use alphabetical order
  find $BASE_DIR/$subdir -name '*.words' | sort | xargs \
    $0 spelling check --known-words /usr/share/dict/words
}

check-one() {
  local words=${1:-_tmp/spelling/_release/VERSION/doc/eggex.words}

  spelling check --known-words /usr/share/dict/words $words
}

check-oil-docs() {
  local dir=_release/VERSION/doc
  check-tree $dir $dir/*.html
}

check-doc-ref() {
  local dir=_release/VERSION/doc/ref
  check-tree $dir $dir/*.html
}

check-blog() {
  # Omit drafts starting with _
  check-tree _site/blog _site/blog/20??/*/[^_]*.html
}

"$@"
