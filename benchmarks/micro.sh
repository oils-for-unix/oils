#!/bin/bash
#
# Benchmarks for small shell snippets.
#
# Usage:
#   ./micro.sh <function name>
#
# TODO: Publish and HTML report with every release.

set -o nounset
set -o pipefail
set -o errexit

# OSH:  583 ms
# bash: 40 ms
# ~10 x
assign-loop() {
  time for i in $(seq 10000); do
    echo x
  done | wc -l
}

# OSH: 176 ms
# bash: 2 ms!
# This is probably mostly because printf is external!
# ~80x
printf-loop() {
  time seq 100 | while read line; do
    printf '%s\n' "$line"
  done | wc -l
}

# This microbenchmark justifies the parse_cache member in
# osh/builtin_printf.py.
#
# With the cache, it runs in ~150 ms.
# Without, it runs in ~230 ms.

printf-loop-complex() {
  time seq 1000 | while read line; do
    printf 'hello \t %s \t %q\n' "$line" 'x y'
  done | wc -l
}

"$@"
