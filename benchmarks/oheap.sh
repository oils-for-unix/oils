#!/bin/bash
#
# Test the size of file, encoding, and decoding speed.
#
# Usage:
#   ./oheap.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

encode-one() {
  local script=$1
  local oheap_out=$2
  bin/osh -n --ast-format oheap "$script" > $oheap_out
}

task-spec() {
  while read path; do
    echo "$path _tmp/oheap/$(basename $path).oheap"
  done < benchmarks/osh-parser-files.txt 
}

run() {
  mkdir -p _tmp/oheap

  local results=_tmp/oheap/results.csv 
  echo 'status,elapsed_secs' > $results

  task-spec | xargs -n 2 --verbose -- \
    benchmarks/time.py --output $results -- \
    $0 encode-one
}

# TODO: instead of running osh_demo, we should generate a C++ program that
# visits every node and counts it.  The output might look like:
#
# - It can also print out the depth of the tree.
# - Summary: number of different types used
# - another option: decode/validate utf-8.  See Visitor Use Cases.
# 
# # 500 instances
# line_span = (...)
# # 455 instances
# token = (
#  id id,
#  string val,    # lengths: min 0, max 20, avg 30
#  int? span_id,
# )
#
#  command = 
#    # 20 instances
#    NoOp   
#    -- TODO: respect order 
#    # 20 instances
#  | SimpleCommand(
#      word* words,        # min length: 0, max: 10, mean: 3.3 ?
#      redir* redirects,   # min length 0, max: 2, mean: 4.4
#      env_pair* more_env)
#  | Sentence(command child, token terminator)
#
# This might help with encoding things inline?
# You will definitely need to append to ASDL arrays.  I don't think you'll need
# to append to strings.  But you might want to store strings inline with
# structs.
# I guess it wouldn't hurt to print out a table of EVERY node an array, along
# with the type.
# parent_type,field_name,type,subtype,length
# token,val,Str,-,5
# SimpleCommand,redirects,Array,redirect,10
#
# This lets you figure out what the common types are, as well as the common
# lengths.

decode() {
  for bin in _tmp/oheap/*.oheap; do
    time _tmp/osh_demo $bin | wc -l
  done
}

stats() {
  ls -l -h _tmp/oheap
  echo
  cat _tmp/oheap/results.csv
}

"$@"
