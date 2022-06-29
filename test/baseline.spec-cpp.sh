#! /bin/bash


#TODO(Jesse): Maybe make another results file for the failures?

output_filename=./baseline.spec-cpp.results

[ -f $output_filname ] && rm $output_filename

for filename in _tmp/spec/cpp/*.tsv; do

  passes="$(cat "$filename" | grep "osh_\.cc\spass" | grep -P -o "\d+")"
  for test_number in $passes; do
    echo -n $test_number >> $output_filename
    echo -n " "          >> $output_filename
    echo -n $filename    >> $output_filename
    echo ""              >> $output_filename
  done

done
