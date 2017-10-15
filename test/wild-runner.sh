#!/bin/bash
#
# Usage:
#   ./wild-runner.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

process-file() {
  local proj=$1
  local abs_path=$2
  local rel_path=$3

  local raw_base=_tmp/wild/raw/$proj/$rel_path
  local www_base=_tmp/wild/www/$proj/$rel_path
  mkdir -p $(dirname $raw_base)
  mkdir -p $(dirname $www_base)

  log "--- Processing $proj - $rel_path"

  # Count the number of lines.  This creates a tiny file, but we're doing
  # everything involving $abs_path at once so it's in the FS cache.
  wc $abs_path > ${raw_base}__wc.txt

  # Make a literal copy with .txt extension, so we can browse it
  cp $abs_path ${www_base}.txt

  # Parse the file.
  local task_file=${raw_base}__parse.task.txt
  local stderr_file=${raw_base}__parse.stderr.txt
  local out_file=${www_base}__ast.html

  run-task-with-status $task_file \
    bin/osh --ast-format abbrev-html -n $abs_path \
    > $out_file 2> $stderr_file

  # Convert the file.
  task_file=${raw_base}__osh2oil.task.txt
  stderr_file=${raw_base}__osh2oil.stderr.txt
  out_file=${www_base}__oil.txt

  run-task-with-status $task_file \
    bin/osh -n --fix $abs_path \
    > $out_file 2> $stderr_file
}

readonly NUM_TASKS=200

print-manifest() {
  #head -n $NUM_TASKS _tmp/wild/MANIFEST.txt
  #egrep '^dokku|^wwwoosh|^oil' _tmp/wild/MANIFEST.txt
  #egrep -- '^pixelb' _tmp/wild/MANIFEST.txt
  #egrep -- '^oil' _tmp/wild/MANIFEST.txt
  cat _tmp/wild/MANIFEST.txt
}

parse-all() {
  local failed=''
  #head -n 20 _tmp/wild/MANIFEST.txt |
  print-manifest | xargs -n 3 -P $JOBS -- $0 process-file || failed=1

  # Limit the output depth
  tree -L 3 _tmp/wild
}

# Takes 3m 47s on 7 cores for 513K lines.
# So that's like 230 seconds or so.  It should really take 1 second!

all-parallel() {
  time {
    test/wild.sh write-manifest
    parse-all
    make-report
  }
}

wild-report() {
  PYTHONPATH=~/hg/json-template/python test/wild_report.py "$@";
}

_link() {
  ln -s -f -v "$@"
}

make-report() {
  print-manifest | wild-report summarize-dirs

  _link \
    $PWD/web/wild.css \
    $PWD/web/osh-to-oil.{html,js,css} \
    $PWD/web/ajax.js \
    $PWD/web/table/table-sort.{js,css} \
    _tmp/wild/www
}

test-wild-report() {
  egrep -- '^oil|^perf-tools' _tmp/wild/MANIFEST.txt | wild-report summarize-dirs
}

if test "$(basename $0)" = 'wild-runner.sh'; then
  "$@"
fi
