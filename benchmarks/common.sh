#!/bin/bash
#
# Common functions for benchmarks.
#

# NOTE: This is in {build,test}/common.sh too.
die() {
  echo "FATAL: $@" 1>&2
  exit 1
}

log() {
  echo "$@" 1>&2
}

csv-concat() {
  tools/csv_concat.py "$@"
}

csv2html() {
  web/table/csv2html.py "$@"
}
