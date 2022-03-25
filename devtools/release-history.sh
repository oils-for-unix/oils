#!/usr/bin/env bash
#
# Usage:
#   devtools/release-history.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh  # R_PATH

readonly ROOT=../oilshell.org__deploy
readonly BASE_DIR=_tmp/release-history

wwz-tsv() {
  find $ROOT/release/ -mindepth 1 -maxdepth 1 -type d | sort | devtools/release_history.py

  # TODO:
  # - Have to sync the .wwz files for some releases.  I really want "vat" here.
}

print-row() {
  local i=0
  for cell in "$@"; do
    if test $i -ne 0; then
      echo -n $'\t'
    fi
    echo -n "$cell"
    i=$((i + 1))
  done
  echo
}

extract-totals() {
  local base_dir=$1

  local -a header=()
  local -a row=()

  IFS=$'\t' read -a header
  #argv "${header[@]}"

  print-row release_date version osh_py_passing osh_cc_passing

  local i=0
  while IFS=$'\t' read -a row; do
    local release_date=${row[0]}
    local version=${row[1]}
    local spec_wwz=${row[2]}
    local survey_path=${row[3]}
    local cpp_summary_path=${row[4]}

    if test $spec_wwz = '-'; then
      continue
    fi
    if test $survey_path = '-'; then
      continue
    fi
    if test $cpp_summary_path = '-'; then
      continue
    fi

    spec_wwz=$PWD/$spec_wwz

    local d=$base_dir/$i
    mkdir -p $d
    pushd $d > /dev/null
    # -o: overwrite without prompting
    unzip -q -o $spec_wwz $survey_path
    unzip -q -o $spec_wwz $cpp_summary_path
    popd > /dev/null

    local osh_py_passing
    osh_py_passing=$(osh-py-passing $d/$survey_path)  # strip trailing newline

    local osh_cpp_passing
    osh_cpp_passing=$(osh-cc-passing $d/$cpp_summary_path)

    print-row "$release_date" $version $osh_py_passing $osh_cpp_passing

    #argv "${row[@]}"

    i=$((i+1))
  done
}

normalize() {
  local path=$1

  # hxselect requires a well-formed XML document
  # NOTE: syntax error on "<tr class=>", but it correctly ignores it
  hxnormalize -x $path > $path.xml || true
}

osh-py-passing() {
  ### Given a file, print the Python total to stdout

  local path=$1

  normalize $path
  hxselect -s $'\n' -c '.totals:nth-child(1) td:nth-child(3)' < $path.xml | head -n 1
}

osh-cc-passing() {
  ### Given a file, print the C++ total to stdout

  local path=$1
  normalize $path

  # Change 1,137 -> 1137
  < $path.xml hxselect -s $'\n' -c '#summary thead tr:nth-child(2) td:nth-child(5)' | sed 's/,//'
}

spec-tsv() {
  rm -r -f -v $BASE_DIR
  mkdir -p $BASE_DIR

  wwz-tsv > $BASE_DIR/wwz.tsv

  < $BASE_DIR/wwz.tsv extract-totals $BASE_DIR | tee $BASE_DIR/spec.tsv

  echo
  wc -l $BASE_DIR/*.tsv
}

show-tsv() {
  cat $BASE_DIR/wwz.tsv | pretty-tsv
  echo
  cat $BASE_DIR/spec.tsv | pretty-tsv
}

report() {
  R_LIBS_USER=$R_PATH devtools/release-history.R $BASE_DIR/spec.tsv $BASE_DIR
}

deps-apt() { 
  # https://superuser.com/questions/528709/command-line-css-selector-tool
  sudo apt-get install html-xml-utils
}

# MEH these tools have bad error messages.
test-parsing() {
  unzip -l $ROOT/release/0.9.8/test/spec.wwz || echo status=$?

  # Annoying syntax for this command
  unzip -p $ROOT/release/0.9.8/test/spec.wwz 'survey/osh.html'  > _tmp/osh.html
  unzip -p $ROOT/release/0.9.8/test/spec.wwz 'cpp/osh-summary.html' > _tmp/osh-summary.html

  local tmp=_tmp

  # hxnormalize makes it XML.
  # NOTE: syntax error on "<tr class=>", but it correctly ignores it
  echo 'PYTHON'
  osh-py-passing _tmp/osh.html 

  osh-cc-passing _tmp/osh-summary.html 
  echo 'CPP'


  return

  # select the rows tagged class="totals", and then the 3rd <td> cell
  cat _tmp/osh.xml | hxselect -s $'\n' -c '.totals td:nth-child(3)' | head -n 1
  echo status=$?

  # select the id="summary" table, then the header
  cat _tmp/osh-summary.xml | hxselect -s $'\n' -c '#summary thead tr:nth-child(2) td:nth-child(5)' | sed 's/,//'
  echo status=$?
}

"$@"
