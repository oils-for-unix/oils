#!/usr/bin/env bash
#
# Benchmarks for YSH JSON
#
# Usage:
#   benchmarks/ysh-for.sh <function name>
#
# TODO: All of these can use BYO
#
# - benchmarks/ysh-for
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

fetch-issues() {
  # only gets 25 issues by default
  # https://docs.github.com/en/rest/issues?apiVersion=2022-11-28

  local n=${1:-100}
  local url="https://api.github.com/repos/oils-for-unix/oils/issues?per_page=$n"

  curl $url > $JSON_FILE

  ls -l -h $JSON_FILE
}

with-ysh() {
  ninja $YSH

  # TODO: turn this into some bigger data

  # 262 ms
  time $YSH -c '
  for i in (1 ..= 1000) {
    json read < $1
  }
  ' dummy $JSON_FILE
}

with-cpython() {
  local prog='
import json
import sys
for i in range(1000):
  with open(sys.argv[1]) as f:
    json.load(f)
'

  # 391 ms
  time python2 -c "$prog" $JSON_FILE

  # 175 ms
  time python3 -c "$prog" $JSON_FILE
}

with-js() {
  # 195 ms, minus ~100 ms startup time = 90 ms
  time cat $JSON_FILE | nodejs -e '
var fs = require("fs")
var stdin = fs.readFileSync(0, "utf-8")

for (let i = 0; i < 1000; ++i) {
  JSON.parse(stdin)
}
'

  # 100 ms startupt ime
  time nodejs -e 'console.log("hi")'

}

with-jq() {
  # TODO: make the data bigger

  # jq is also printing it here - we can take the length
  time jq '. | length' < $JSON_FILE
}


compare() {
  local n=${1:-1000000}
  local OILS_GC_STATS=${2:-}

  ninja $OSH $YSH

  for bin in ysh cpython js jq; do
    echo "=== $bin ==="
    with-$bin
    echo
  done
}

"$@"
