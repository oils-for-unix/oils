#!/bin/bash
#
# Common functions for benchmarks.
#

csv-concat() {
  tools/csv_concat.py "$@"
}

csv2html() {
  web/table/csv2html.py "$@"
}
