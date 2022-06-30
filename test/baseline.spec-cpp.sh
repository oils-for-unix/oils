#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset

#TODO(Jesse): Maybe make another results file for the failures?

output_filename=./test/baseline.spec-cpp.results

[ -f $output_filename ] && rm $output_filename

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
    echo "$test_number $filename" >> $output_filename
  done

done
