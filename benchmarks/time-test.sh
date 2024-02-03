#!/usr/bin/env bash
#
# Usage:
#   benchmarks/time-test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source test/common.sh
source test/tsv-lib.sh

# TODO: This would be a nice little program for Oil
count-lines-and-cols() {
  python2 -c '
import sys

expected_num_lines = int(sys.argv[1])
expected_num_cols = int(sys.argv[2])
try:
  sep = sys.argv[3]
except IndexError:
  sep = "\t"

num_lines = 0
tab_counts = []
for line in sys.stdin:
  tab_counts.append(line.count(sep))
  num_lines += 1
  # Show what we get
  sys.stdout.write(line)

if any(tab_counts[0] != n for n in tab_counts):
  raise AssertionError(tab_counts)

num_tabs = tab_counts[0]

assert expected_num_lines == num_lines, \
  "expected %d lines, got %d" % (expected_num_lines, num_lines)
assert expected_num_cols == num_tabs + 1, \
  "expected %d cols, got %d" % (expected_num_cols, num_tabs + 1)
' "$@"
}

time-tool() {
  $(dirname $0)/time_.py "$@"
}

test-csv() {
  local out=_tmp/time.csv

  time-tool -o $out -- echo hi
  cat $out | count-lines-and-cols 1 2 ,

  time-tool -o $out --field a --field b -- echo hi
  cat $out | count-lines-and-cols 1 4 ,

  time-tool -o $out --rusage -- echo hi
  cat $out | count-lines-and-cols 1 5 ,

  time-tool -o $out --rusage --field a --field b -- echo hi
  cat $out | count-lines-and-cols 1 7 ,
}

test-tsv() {
  local out=_tmp/time.tsv
  rm -f $out

  for i in 1 2 3; do
    time-tool --tsv -o $out --append --time-fmt '%.2f' -- sleep 0.0${i}
  done
  cat $out | count-lines-and-cols 3 2

  time-tool --tsv -o $out --field a --field b -- echo hi
  cat $out | count-lines-and-cols 1 4 

  time-tool --tsv -o $out --rusage --field a --field b -- echo hi
  cat $out | count-lines-and-cols 1 7
}

test-append() {
  local out=_tmp/overwrite.tsv
  for i in 4 5; do
    time-tool --tsv -o $out -- sleep 0.0${i}
  done
  cat $out | count-lines-and-cols 1 2

  echo ---

  local out=_tmp/append.tsv
  rm -f $out

  for i in 4 5; do
    time-tool --tsv -o $out --append -- sleep 0.0${i}
  done
  cat $out | count-lines-and-cols 2 2
}

test-usage() {
  # no args
  set +o errexit

  time-tool; status=$?
  assert $status -eq 2

  time-tool --output; status=$?
  assert $status -eq 2

  time-tool sleep 0.1
  time-tool --append sleep 0.1; status=$?
  assert $status -eq 0

  set -o errexit
}

test-bad-tsv-chars() {
  local out=_tmp/time2.tsv
  rm -f $out

  set +o errexit

  # Newline should fail
  time-tool --tsv -o $out --field $'\n' -- sleep 0.001; status=$?
  assert $status -eq 1

  # Tab should fail
  time-tool --tsv -o $out --field $'\t' -- sleep 0.001; status=$?
  assert $status -eq 1

  # Quote should fail
  time-tool --tsv -o $out --field '"' -- sleep 0.001; status=$?
  assert $status -eq 1

  # Backslash is OK
  time-tool --tsv -o $out --field '\' -- sleep 0.001; status=$?
  assert $status -eq 0

  # Space is OK, although canonical form would be " "
  time-tool --tsv -o $out --field ' ' -- sleep 0.001; status=$?
  assert $status -eq 0

  set -o errexit

  cat $out

  echo $'OK\ttest-bad-tsv-chars'
}

test-stdout() {
  local out=_tmp/time-stdout.csv
  time-tool -o $out --stdout _tmp/stdout.txt -- seq 3

  diff _tmp/stdout.txt - <<EOF
1
2
3
EOF

  # No assertions here yet
  md5sum _tmp/stdout.txt
  cat $out | count-lines-and-cols 1 3 ,

  time-tool -o $out --rusage --stdout _tmp/stdout.txt -- seq 3
  cat $out | count-lines-and-cols 1 6 ,
}

test-rusage() {
  local out=_tmp/time-rusage.csv
  time-tool --tsv -o $out --rusage -- bash -c 'echo bash'
  cat $out | count-lines-and-cols 1 5

  #time-tool --tsv -o $out --rusage -- dash -c 'echo dash'
  #cat $out

  # Blow up memory size for testing
  local py='a=[42]*500000; print "python"'

  time-tool --tsv -o $out --rusage -- python2 -c "$py"
  cat $out | count-lines-and-cols 1 5

  #time-tool --tsv -o $out --rusage -- bin/osh -c 'echo osh'
  #cat $out
}

test-time-span() {
  local out=_tmp/time-span.csv

  time-tool --tsv -o $out --time-span --print-header
  cat $out | count-lines-and-cols 1 4

  time-tool --tsv -o $out --time-span -- bash -c 'echo bash'
  cat $out | count-lines-and-cols 1 4
}

# Compare vs. /usr/bin/time.
test-maxrss() {
  if which time; then  # Ignore this on continuous build
    command time --format '%x %U %M' -- seq 1
  fi

  # Showing a discrepancy.  FIXED!
  time-tool -o _tmp/maxrss --tsv --rusage -- seq 1
  cat _tmp/maxrss
}

test-print-header() {
  set +o errexit

  # no arguments allowed
  time-tool --tsv --print-header foo bar
  assert $? -eq 2

  time-tool --tsv --print-header --field name
  assert $? -eq 0

  time-tool --tsv --print-header --rusage --field name
  assert $? -eq 0

  time-tool --print-header --rusage --field foo --field bar
  assert $? -eq 0

  time-tool -o _tmp/time-test-1 \
    --print-header --rusage --stdout DUMMY --tsv --field a --field b
  assert $? -eq 0

  #set -x
  head _tmp/time-test-1
}

test-time-helper() {
  set +o errexit

  local tmp=_tmp/time-helper.txt

  local th=_devbuild/bin/time-helper

  # Make some work show up
  local cmd='{ md5sum */*.md; sleep 0.15; exit 42; } > /dev/null'

  echo 'will be overwritten' > $tmp
  cat $tmp

  $th
  assert $? -ne 0  # it's 1, but could be 2

  $th /bad
  assert $? -eq 1

  $th -o $tmp -d $'\t' -x -e -- sh -c "$cmd"
  assert $? -eq 42
  cat $tmp
  echo

  # Now append
  $th -o $tmp -a -d , -x -e -U -S -M -- sh -c "$cmd"
  assert $? -eq 42
  cat $tmp
  echo
  
  # Error case
  $th -q
  assert $? -eq 2
}

test-time-tsv() {
  local status

  local out=_tmp/time-test-zz
  rm -f -v $out

  # Similar to what soil/worker.sh does
  set +o errexit
  time-tsv -o $out --append -- zz
  status=$?
  set -o errexit

  echo status=$status
  assert $status -eq 1

  cat $out
  echo
}

test-grandchild-memory() {
  local -a use_mem=( python2 -c 'import sys; ["X" * int(sys.argv[1])]' 10000000 )

  time-tsv -o /dev/stdout --rusage -- "${use_mem[@]}"

  # RUSAGE_CHILDREN includes grandchildren!
  time-tsv -o /dev/stdout --rusage -- sh -c 'echo; "$@"' dummy "${use_mem[@]}"

  # 'exec' doesn't make a consistent difference, because /bin/sh doesn't use
  # much memory
  time-tsv -o /dev/stdout --rusage -- sh -c 'echo; exec "$@"' dummy "${use_mem[@]}"
}

soil-run() {
  run-test-funcs
}

"$@"
