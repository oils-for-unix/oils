# TSV utilities
#
# Usage:
#   source test/tsv-lib.sh

test -n "${__TEST_TSV_LIB_SH:-}" && return
readonly __TEST_TSV_LIB_SH=1

if test -z "${REPO_ROOT:-}"; then
  echo "${BASH_SOURCE[0]}: \$REPO_ROOT must be set before sourcing" >&2
  exit 2
fi

readonly TAB=$'\t'

time-tsv() {
  ### Run a task and output TSV
  $REPO_ROOT/benchmarks/time_.py --tsv "$@"
}

time-tsv3() {
  ### Maybe run with python3, our CI VMs don't have python2

  # Some Soil tasks like dev-setup-* and raw-vm run on the VM, with python3, not python2
  # Others run in a container with python2, not python3 (this may go away)

  if command -v python3 >/dev/null; then
    python3 $REPO_ROOT/benchmarks/time_.py --tsv "$@"
  else
    $REPO_ROOT/benchmarks/time_.py --tsv "$@"
  fi
}

tsv2html() {
  ### Convert TSV to an HTML table
  $REPO_ROOT/web/table/csv2html.py --tsv "$@"
}

tsv2html3() {
  ### Convert TSV to an HTML table
  python3 $REPO_ROOT/web/table/csv2html.py --tsv "$@"
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

  while read -r one two; do
    echo "${one}${TAB}${two}"
  done
}

here-schema-tsv-3col() {
  ### As above, with 3 cols
  while read -r one two three; do
    echo "${one}${TAB}${two}${TAB}${three}"
  done
}

here-schema-tsv-4col() {
  ### As above, with 4 cols
  while read -r one two three four; do
    echo "${one}${TAB}${two}${TAB}${three}${TAB}${four}"
  done
}


tsv-concat() {
  devtools/tsv_concat.py "$@"
}

# TSV and CSV concatenation are actually the same.  Just use the same script.
csv-concat() {
  devtools/tsv_concat.py "$@"
}

tsv-add-const-column() {
  ### Used to add a host name to GC stats

  local col_name=$1
  local const_value=$2

  local i=0
  while read -r line; do
    if test $i = 0; then
      echo -n "$col_name$TAB"
    else
      echo -n "$const_value$TAB"
    fi
    # Print the other columns
    printf '%s\n' "$line"

    i=$((i+1))
  done
}
