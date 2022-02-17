# TSV utiltiies
#
# Usage:
#   source test/tsv-lib.sh

time-tsv() {
  ### Run a task and output TSV
  benchmarks/time_.py --tsv "$@"
}

tsv2html() {
  ### Convert TSV to an HTML table
  web/table/csv2html.py --tsv "$@"
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

