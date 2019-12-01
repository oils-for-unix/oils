#!/bin/bash
#
# Usage:
#   ./wild-runner.sh <function name>

set -o nounset
set -o pipefail
set -o errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

source test/common.sh

dump-html-and-translate-file() {
  local rel_path=$1
  local abs_path=$2

  local raw_base=_tmp/wild/raw/$rel_path
  local www_base=_tmp/wild/www/$rel_path
  mkdir -p $(dirname $raw_base) $(dirname $www_base)

  log "--- Processing $rel_path"

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
    bin/oshc translate $abs_path \
    > $out_file 2> $stderr_file
}

# In case we built with ASAN
export ASAN_OPTIONS='detect_leaks=0'

dump-text-for-file() {
  local rel_path=$1
  local abs_path=$2

  local py_base=_tmp/wild/py/$rel_path
  local cpp_base=_tmp/wild/cpp/$rel_path

  mkdir -p $(dirname $py_base) $(dirname $cpp_base)

  log "--- Processing $rel_path"

  # Parse the file with Python
  local task_file=${py_base}.task.txt
  local stderr_file=${py_base}.stderr.txt
  local out_file=${py_base}.ast.txt

  run-task-with-status $task_file \
    bin/osh --ast-format text -n $abs_path \
    > $out_file #2> $stderr_file

  # Parse the file with C++
  local task_file=${cpp_base}.task.txt
  local stderr_file=${cpp_base}.stderr.txt
  local out_file=${cpp_base}.ast.txt

  run-task-with-status $task_file \
    _bin/osh_parse.asan $abs_path \
    > $out_file #2> $stderr_file
}


readonly NUM_TASKS=200
readonly MANIFEST=_tmp/wild/MANIFEST.txt

parse-in-parallel() {
  local func=${1:-dump-html-and-translate-file}

  local failed=''
  xargs -n 2 -P $JOBS -- $0 $func || failed=1

  # Limit the output depth
  tree -L 3 _tmp/wild
}

# Takes 3m 47s on 7 cores for 513K lines.
# So that's like 230 seconds or so.  It should really take 1 second!

parse-and-report() {
  local manifest_regex=${1:-}  # egrep regex for manifest line
  local func=${2:-dump-html-and-translate-file}

  time {
    #test/wild.sh write-manifest
    test/wild.sh manifest-from-archive

    if test -n "$manifest_regex"; then
      egrep -- "$manifest_regex" $MANIFEST | parse-in-parallel $func
    else
      cat $MANIFEST | parse-in-parallel $func
    fi

    make-report
  }
}

dump-text-asts() {
  local manifest_regex=${1:-}  # egrep regex for manifest line

  local func=dump-text-for-file

  if test -n "$manifest_regex"; then
    egrep -- "$manifest_regex" $MANIFEST | parse-in-parallel $func
  else
    cat $MANIFEST | parse-in-parallel $func
  fi
}

compare-one-ast() {
  local left=$1

  local old='/py/'
  local new='/cpp/'
  local right=${left/$old/$new}

  #echo $left $right
  diff -q -u $left $right
  #md5sum $left $right
}

compare-asts() {
  local manifest=_tmp/wild/compare.txt
  find _tmp/wild/py -name '*.ast.txt' > $manifest

  log "Comparing ..."
  wc -l $manifest
  echo

  cat $manifest | xargs -n 1 -- $0 compare-one-ast
}

# NOTE: This depends on test/jsontemplate.py.  Should we make that part of
# 'deps'?
wild-report() {
  test/wild_report.py "$@"
}

_link() {
  ln -s -f -v "$@"
}

version-text() {
  date-and-git-info
  echo "\$ $OSH --version"
  $OSH --version
}

make-report() {
  local in_dir=_tmp/wild/raw
  local out_dir=_tmp/wild/www

  # TODO: This could also go in 'raw', and then be processed by Python?
  version-text > $out_dir/version-info.txt

  cat $MANIFEST | wild-report summarize-dirs \
    --not-shell test/wild-not-shell.txt \
    --not-osh test/wild-not-osh.txt \
    $in_dir $out_dir

  # This has to go inside the www dir because of the way that relative links
  # are calculated.
  # TODO: Isn't this redundant?
  _link $PWD/web/osh-to-oil.{html,js} $out_dir
  _link $PWD/web _tmp
}

test-wild-report() {
  egrep -- '^oil|^perf-tools' $MANIFEST | wild-report summarize-dirs
}

if test "$(basename $0)" = 'wild-runner.sh'; then
  "$@"
fi
