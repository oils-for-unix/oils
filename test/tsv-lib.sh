# TSV utiltiies
#
# Usage:
#   source test/tsv-lib.sh

if test -z "${REPO_ROOT:-}"; then
  echo "${BASH_SOURCE[0]}: \$REPO_ROOT must be set before sourcing" >&2
  exit 2
fi

time-tsv() {
  ### Run a task and output TSV
  $REPO_ROOT/benchmarks/time_.py --tsv "$@"
}

tsv2html() {
  ### Convert TSV to an HTML table
  $REPO_ROOT/web/table/csv2html.py --tsv "$@"
}

tsv-row() {
  ### Usage: tsv-row a b c
  local i=0
  for cell in "$@"; do
    if test $i -ne 0; then
      echo -n $'\t'
    fi

    # note: if this were QTT, then it would be quoted
    echo -n "$cell"

    i=$((i + 1))
  done

  echo  # newline
}

here-schema-tsv() {
  ### Read a legible text format on stdin, and write TSV on stdout

  local tab=$'\t'
  while read one two; do
    echo "${one}${tab}${two}"
  done
}
