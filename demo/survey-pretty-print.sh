#!/usr/bin/env bash
#
# Survey pretty printing
#
# Usage:
#   demo/survey-pretty-print.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

pretty() {
  # Python doesn't do pretty printing, but we could try this module
  #
  # https://github.com/tommikaikkonen/prettyprinter

  echo 'Python'
  python3 -c '
d = {}
for i in range(20):
  d[i] = i

d[0] = []
for i in range(30):
  d[0].append(i)

d[9] = lambda x: x

print(d)
'

  echo 

  # node.js does some line wrapping with color, with console.log().  
  # It might be their own REPL, or built into v8.
  echo 'JS'
  nodejs -e '
var d = {}
for (var i = 0; i < 20; ++i) {
  d[i] = i;
}

d[0] = [];
for (var i = 0; i < 30; ++i) {
  d[0].push(i);
}

d[19] = [];
for (var i = 0; i < 50; ++i) {
  d[19].push(i);
}

d[19][12] = {"k": "v"};

d[9] = function (x) { return x; }

// Causes fancier columns
d[0][8] = function (x) { return x; }

console.log(d)
'
  echo 

  # - Do Perl and Ruby do any printing?  IRB is Ruby's REPL
  # - Lua and awk don't do any pretty printing AFAIK
}

"$@"
