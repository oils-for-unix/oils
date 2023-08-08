#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset

#TODO(Jesse): Maybe make another results file for the failures?

test_passes_filename=test/baseline.spec-cpp.results
assertion_fails_filename=test/baseline.spec-cpp.assertion_fails

tmp_file_0=_tmp/spec/cpp/file_0
tmp_file_1=_tmp/spec/cpp/file_1


[ -f $test_passes_filename ] && rm $test_passes_filename
[ -f $assertion_fails_filename ] && rm $assertion_fails_filename

find_passing_tests()
{
  cat "$filename" | grep "osh_\.cc\spass" | grep -P -o "\d+"
}

allow_errors()
{
  true
}

echo "Parsing Results"
for filename in _tmp/spec/cpp/*.tsv; do


  passes=$(find_passing_tests || allow_errors)
  for test_number in $passes; do
    echo "$test_number $filename" >> $test_passes_filename
  done

done

[ -f $tmp_file_0 ] && rm $tmp_file_0
[ -f $tmp_file_1 ] && rm $tmp_file_1
grep "Assertion.*failed\." _tmp/spec/cpp/* > $tmp_file_0

echo "Recording Assertion Failures"
while read -r line; do
  assert_fail=$(echo -n "$line" | grep -o -P "oils-for-unix: \K.*") || allow_errors
  test_fail=$(echo "$line" | cut -d: -f1) || allow_errors
  echo "($assert_fail) $test_fail" >> $tmp_file_1
done < $tmp_file_0

sort $tmp_file_1 > $assertion_fails_filename

[ -f $tmp_file_0 ] && rm $tmp_file_0
grep "OSH_CPP_SEGFAULT" _tmp/spec/cpp/* > $tmp_file_0

echo "Recording Segfaults"
while read -r line; do
  echo "IF YOU SEE THIS OSH IS CRASHING ($line)" >> $assertion_fails_filename
done < $tmp_file_0

