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

"$@"
