#!/usr/bin/env bash
#
# Benchmarks for YSH JSON
#
# Usage:
#   benchmarks/ysh-for.sh <function name>
#
# TODO: All of these can use BYO
#
# - benchmarks/ysh-json
# - benchmarks/io/read-lines.sh  # buffered and unbuffered, not hooked up
# - benchmarks/compute
#   - control-flow with exceptions - slower than other shells
#   - word-split - faster
#
# Also:
# - ovm-build should be added to CI

set -o nounset
set -o pipefail
set -o errexit

YSH=_bin/cxx-opt/ysh
OSH=_bin/cxx-opt/osh

readonly JSON_FILE=_tmp/github-issues.json
readonly BIG_FILE=_tmp/compute/big.json

fetch-issues() {
  # only gets 25 issues by default
  # https://docs.github.com/en/rest/issues?apiVersion=2022-11-28

  local n=${1:-100}
  local url="https://api.github.com/repos/oils-for-unix/oils/issues?per_page=$n"

  curl $url > $JSON_FILE

  ls -l -h $JSON_FILE

  jq \
    -s \
    --arg n "$n" \
    '. as $original | [range(0; $n|tonumber)] | map($original) | flatten' \
    $JSON_FILE > $BIG_FILE

  ls -l -h $BIG_FILE
}

with-ysh() {
  local n=${1:-100}
  ninja $YSH

if false; then

  time $YSH -c '
  var n = int($2)
  for i in (1 ..= n) {
    json read < $1
  }
  ' dummy $JSON_FILE $n
fi

  echo '  YSH'
  time $YSH -c 'json read < $1' dummy $BIG_FILE
}

with-cpython() {
  local n=${1:-100}

if false; then
  local prog='
import json
import sys
n = int(sys.argv[2])
for i in range(n):
  with open(sys.argv[1]) as f:
    json.load(f)
'

  echo 'PY2'
  # 391 ms
  time python2 -c "$prog" $JSON_FILE $n

  echo 'PY3'
  # 175 ms
  time python3 -c "$prog" $JSON_FILE $n
fi

  local prog='
import json
import sys
with open(sys.argv[1]) as f:
  json.load(f)
'

  echo 'PY2'
  # 391 ms
  time python2 -c "$prog" $BIG_FILE

  echo 'PY3'
  # 175 ms
  time python3 -c "$prog" $BIG_FILE
}

with-js() {
  local n=${1:-100}

if false; then
  # 195 ms, minus ~100 ms startup time = 90 ms
  time nodejs -e '
var fs = require("fs")
var filename = process.argv[1];
var n = process.argv[2];

//console.log("FILE " + filename);
var json = fs.readFileSync(filename, "utf-8");

for (let i = 0; i < n; ++i) {
  JSON.parse(json)
}
' $JSON_FILE $n
fi

  time nodejs -e '
var fs = require("fs")
var filename = process.argv[1];

//console.log("FILE " + filename);
var json = fs.readFileSync(filename, "utf-8");

JSON.parse(json)
' $BIG_FILE

  # 100 ms startup time is misleading
  #time nodejs -e 'console.log("hi")' 
}

with-jq() {
  local n=${1:-100}

  wc -l $JSON_FILE

  time jq '. | length' $BIG_FILE >/dev/null
}


compare() {
  local n=${1:-100}
  local OILS_GC_STATS=${2:-}

  ninja $OSH $YSH

  for bin in ysh cpython js jq; do
    echo "=== $bin ==="
    with-$bin $n
    echo
  done
}

"$@"
