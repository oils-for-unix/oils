#!/usr/bin/env bash
#
# Usage:
#   ./spelling.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly BASE_DIR=_tmp/spelling

to-ninja() {
  echo '
rule text-dump
  command = lynx -dump $in > $out
  description = text-dump $in $out

rule word-split
  command = cat $in | doctools/spelling.py word-split > $out
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

doc-to-text() {
  local base_dir=$1
  find $base_dir -name '*.html' | to-ninja > _tmp/doc.ninja
  ninja -f _tmp/doc.ninja
}

clean() {
  rm -r -f -v $BASE_DIR
}

check-docs() {
  # Depends on build/doc.sh all-markdown
  doc-to-text _release/VERSION/doc

  # Complete word count
  find $BASE_DIR -name '*.words' | xargs wc -l
  #return

  find $BASE_DIR -name '*.words' | xargs \
    doctools/spelling.py check --known-words /usr/share/dict/words
  return

  find $BASE_DIR -name '*.words' | while read path; do
    echo $path
    echo ====
    spell $path
    echo ====
  done
}

"$@"
