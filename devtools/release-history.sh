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
  mkdir -p $BASE_DIR

  find $ROOT/release/ -mindepth 1 -maxdepth 1 -type d \
    | sort \
    | devtools/release_history.py > $BASE_DIR/wwz.tsv

  wc -l $BASE_DIR/wwz.tsv

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

  while IFS=$'\t' read -a row; do
    local release_date=${row[0]}
    local version=${row[1]}
    local spec_wwz=${row[2]}
    local survey_path=${row[3]}
    local cpp_summary_path=${row[4]}

    if test $spec_wwz = '-'; then
      continue
    fi

    spec_wwz=$PWD/$spec_wwz

    local d=$base_dir/tmp/$version
    mkdir -p $d

    pushd $d > /dev/null

    # -o: overwrite without prompting

    local osh_py_passing='NA'
    if test $survey_path != '-'; then
      unzip -q -o $spec_wwz $survey_path
      osh_py_passing=$(osh-py-passing $survey_path)  # strip trailing newline
    fi

    local osh_cpp_passing='NA'
    if test $cpp_summary_path != '-'; then
      unzip -q -o $spec_wwz $cpp_summary_path
      osh_cpp_passing=$(osh-cc-passing $cpp_summary_path)
    fi

    popd > /dev/null

    print-row "$release_date" "$version" "$osh_py_passing" "$osh_cpp_passing"

    #argv "${row[@]}"
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
  # This works for recent ones, with header at the top
  #hxselect -s $'\n' -c '.totals:nth-child(1) td:nth-child(3)' < $path.xml | head -n 1

  # Older ones: total is in footer
  #hxselect -s $'\n' -c 'tfoot td:nth-child(3)' < $path.xml

  log "path = $path"
  local name
  name=$(basename $path)


  # TODO:
  # - Extract tfoot cells 3 and 5
  # - Extract head cells 3 and 5 -- description
  # - And then in R, select the right one for osh_py_passing

  if test "$name" = 'index.html'; then
    # It might be 3 or 5 -- I moved the columns around
    local count

    count=$(hxselect -s $'\n' -c 'tfoot td:nth-child(5)' < $path.xml)

    # Differing format
    if test "$count" -lt 100; then
      count=$(hxselect -s $'\n' -c 'tfoot td:nth-child(3)' < $path.xml)
    fi
    echo "$count"

  else
    hxselect -s $'\n' -c '.totals:nth-child(1) td:nth-child(3)' < $path.xml | head -n 1
  fi
}

osh-cc-passing() {
  ### Given a file, print the C++ total to stdout

  local path=$1
  normalize $path

  # Change 1,137 -> 1137
  < $path.xml hxselect -s $'\n' -c '#summary thead tr:nth-child(2) td:nth-child(5)' | sed 's/,//'
}

spec-tsv() {
  rm -r -f -v $BASE_DIR/tmp  # extract-totals writes to this dir

  < $BASE_DIR/wwz.tsv extract-totals $BASE_DIR | tee $BASE_DIR/spec.tsv

  echo
  wc -l $BASE_DIR/*.tsv
}

tsv-preview() {
  cat $BASE_DIR/wwz.tsv | pretty-tsv
  echo
  cat $BASE_DIR/spec.tsv | pretty-tsv
}

report() {
  R_LIBS_USER=$R_PATH devtools/release-history.R $BASE_DIR $BASE_DIR
}

copy() {
  cp -v $BASE_DIR/spec-test-history-2.png ../oilshell.org__deploy/blog/2022/03
}

deps-apt() { 
  # https://superuser.com/questions/528709/command-line-css-selector-tool
  sudo apt-get install html-xml-utils
}

# MEH these tools have bad error messages.
test-parsing() {
  unzip -l $ROOT/release/0.9.8/test/spec.wwz || echo status=$?

  unzip -p $ROOT/release/0.9.8/test/spec.wwz 'cpp/osh-summary.html' > _tmp/osh-summary.html

  local tmp=_tmp

  # hxnormalize makes it XML.
  # NOTE: syntax error on "<tr class=>", but it correctly ignores it
  echo
  echo 'NEW PYTHON'
  # Annoying syntax for this command
  unzip -p $ROOT/release/0.9.8/test/spec.wwz 'survey/osh.html'  > _tmp/osh.html
  osh-py-passing _tmp/osh.html

  echo
  echo 'OLD PYTHON 0.7.pre3'
  unzip -p $ROOT/release/0.7.pre3/test/spec.wwz 'index.html' > _tmp/index.html
  osh-py-passing _tmp/index.html

  echo
  echo 'OLD PYTHON 0.2.0'
  unzip -p $ROOT/release/0.2.0/test/spec.wwz 'index.html' > _tmp/index.html
  osh-py-passing _tmp/index.html

  echo
  echo 'CPP'
  osh-cc-passing _tmp/osh-summary.html 
}

"$@"
