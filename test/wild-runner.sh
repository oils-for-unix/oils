#!/bin/bash
#
# Usage:
#   ./wild-runner.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

process-file() {
  local rel_path=$1
  local abs_path=$2

  local raw_base=_tmp/wild/raw/$rel_path
  local www_base=_tmp/wild/www/$rel_path
  mkdir -p $(dirname $raw_base)
  mkdir -p $(dirname $www_base)

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
    $OSH --fix $abs_path \
    > $out_file 2> $stderr_file
}

readonly NUM_TASKS=200
readonly MANIFEST=_tmp/wild/MANIFEST.txt

parse-in-parallel() {
  local failed=''
  xargs -n 2 -P $JOBS -- $0 process-file || failed=1

  # Limit the output depth
  tree -L 3 _tmp/wild
}

# Takes 3m 47s on 7 cores for 513K lines.
# So that's like 230 seconds or so.  It should really take 1 second!

parse-and-report() {
  local manifest_regex=${1:-}  # egrep regex for manifest line

  time {
    #test/wild.sh write-manifest
    test/wild.sh manifest-from-archive

    if test -n "$manifest_regex"; then
      egrep -- "$manifest_regex" $MANIFEST | parse-in-parallel
    else
      cat $MANIFEST | parse-in-parallel
    fi

    make-report
  }
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
