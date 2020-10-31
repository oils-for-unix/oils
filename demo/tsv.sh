#!/usr/bin/env bash
#
# Usage:
#   ./tsv.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# https://www.stefaanlippens.net/pretty-csv.html

# Features missing:
# - right justification of numbers
#   - rounding numbers for eyeballing?
# - changing width interactively?
# - would be nice to have a cursor
# - optional prettification
#   - column headings, maybe https://qtsv.org line

pretty-tsv() {
  column -t -s $'\t' -n "$@" | less -F -S -X -K
}

demo() {
  pretty-tsv ../benchmark-data/compute/bubble_sort/*.tsv
}


# https://stackoverflow.com/questions/1875305/view-tabular-file-such-as-csv-from-command-line
#
# Others:
# - csvtool
# - csvkit with csvlook
# - https://github.com/codechenx/tv

"$@"
