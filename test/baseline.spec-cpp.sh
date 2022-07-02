#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset

#TODO(Jesse): Maybe make another results file for the failures?

test_passes_filename=test/baseline.spec-cpp.results
tmp_assertion_fails_0=_tmp/spec/cpp/assertion_fails_0
tmp_assertion_fails_1=_tmp/spec/cpp/assertion_fails_1
assertion_fails_filename=test/baseline.spec-cpp.assertion_fails

[ -f $test_passes_filename ] && rm $test_passes_filename
[ -f $assertion_fails_filename ] && rm $assertion_fails_filename
[ -f $tmp_assertion_fails_0 ] && rm $tmp_assertion_fails_0
[ -f $tmp_assertion_fails_1 ] && rm $tmp_assertion_fails_1

find_passing_tests()
{
  cat "$filename" | grep "osh_\.cc\spass" | grep -P -o "\d+"
}

allow_errors()
{
  true
}

for filename in _tmp/spec/cpp/*.tsv; do

  passes=$(find_passing_tests || allow_errors)
  for test_number in $passes; do
    echo "$test_number $filename" >> $test_passes_filename
  done

done

grep "Assertion.*failed\." _tmp/spec/cpp/* > $tmp_assertion_fails_0

while read -r line; do
  assert_fail=$(echo -n "$line" | grep -o -P "osh_eval: \K.*") || allow_errors
  test_fail=$(echo "$line" | cut -d: -f1) || allow_errors
  echo "($assert_fail) $test_fail" >> $tmp_assertion_fails_1
done < $tmp_assertion_fails_0

sort $tmp_assertion_fails_1 > $assertion_fails_filename

