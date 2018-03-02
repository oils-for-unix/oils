#!/bin/bash
#
# Test the size of file, encoding, and decoding speed.
#
# Usage:
#   ./oheap.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh
source benchmarks/common.sh

readonly BASE_DIR=_tmp/oheap

encode-one() {
  local script=$1
  local oheap_out=$2
  $OSH_OVM -n --ast-format oheap "$script" > $oheap_out
}

task-spec() {
  while read path; do
    echo "$path _tmp/oheap/$(basename $path)__oheap"
  done < benchmarks/osh-parser-files.txt 
}

encode-all() {
  mkdir -p _tmp/oheap

  local times_csv=_tmp/oheap/times.csv
  echo 'status,elapsed_secs' > $times_csv

  task-spec | xargs -n 2 --verbose -- \
    benchmarks/time.py --output $times_csv -- \
    $0 encode-one
}

# Out of curiousity, compress oheap and originals.

compress-oheap() {
  local c_dir=$BASE_DIR/oheap-compressed
  mkdir -p $c_dir
  for bin in _tmp/oheap/*__oheap; do
    local name=$(basename $bin)
    log "Compressing $name"
    gzip --stdout $bin > $c_dir/$name.gz
    xz --stdout $bin > $c_dir/$name.xz
  done
}

compress-text() {
  local c_dir=$BASE_DIR/src-compressed
  mkdir -p $c_dir

  while read src; do
    local name=$(basename $src)
    log "Compressing $name"
    gzip --stdout $src > $c_dir/${name}__text.gz
    xz --stdout $src > $c_dir/${name}__text.xz
  done < benchmarks/osh-parser-files.txt 
}

print-size() {
  local c1=$1
  local c2=$2
  shift 2

  # depth 0: just the filename itself.
  find "$@" -maxdepth 0 -printf "%s,$c1,$c2,%p\n"
}

print-csv() {
  echo 'num_bytes,format,compression,path'
  # TODO
  print-size text none benchmarks/testdata/*
  print-size text gz $BASE_DIR/src-compressed/*.gz
  print-size text xz $BASE_DIR/src-compressed/*.xz

  print-size oheap none $BASE_DIR/*__oheap
  print-size oheap gz $BASE_DIR/oheap-compressed/*.gz
  print-size oheap xz $BASE_DIR/oheap-compressed/*.xz 
}

# This can be done on any host.
measure() {
  encode-all
  compress-oheap
  compress-text
}

stage1() {
  local out_dir=$BASE_DIR/stage1
  mkdir -p $out_dir
  print-csv > $out_dir/sizes.csv
}

print-report() {
  local in_dir=$1
  local base_url='../../web'

  cat <<EOF
<!DOCTYPE html>
<html>
  <head>
    <title>OHeap Encoding</title>
    <script type="text/javascript" src="$base_url/table/table-sort.js"></script>
    <link rel="stylesheet" type="text/css" href="$base_url/table/table-sort.css" />
    <link rel="stylesheet" type="text/css" href="$base_url/benchmarks.css" />

  </head>
  <body>
    <p id="home-link">
      <a href="/">oilshell.org</a>
    </p>
    <h2>OHeap Encoding</h2>

    <h3>Encoding Size (KB)</h3>

    <p>Sizes are in KB (powers of 10), not KiB (powers of 2).</p>
EOF
  csv2html $in_dir/encoding_size.csv

  cat <<EOF
    <h3>Encoding Ratios</h3>
EOF
  csv2html $in_dir/encoding_ratios.csv

  cat <<EOF
  </body>
</html>
EOF
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

"$@"
