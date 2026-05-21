#!/usr/bin/env bash
#
# Usage:
#   devtools/release-history.sh <function name>
#
# Examples:
#   $0 do-all 
#   $0 wwz-tsv - release metadata
#   $0 spec-tsv - specific numbers
#   $0 make-plot
#
# This is actually similar to the "parallel process table pattern"
# I guess it's just the "process table pattern", since it's serial

set -o nounset
set -o pipefail
set -o errexit

source build/dev-shell.sh  # R_LIBS_USER

# PROBLEM: we need to use ggplot2.  Should I update the wedge?  That would be
# the right thing to do.  Then I have to update all containers and all that.
# Maybe I need another wedge with ggplot2

#readonly ROOT=../../oilshell/oilshell.org__deploy
# A version I synced
readonly ROOT=../../oilshell/oilshell.org-2025-12-16
readonly ROOT_OILS=../oils.pub__deploy

readonly BASE_DIR=_tmp/release-history

die() {
  echo "FATAL: $@" >& 2
  exit 1
}

release-dirs() {
  find $ROOT/release/ $ROOT_OILS/release/ -mindepth 1 -maxdepth 1 -type d
}

# Python file has
# HEADER=('date', 'version', 'spec_wwz', 'osh_py_path', 'osh_cpp_path')
#
# parses release-date.txt for the date
# So I need to unify oils.pub and oilshell.org

wwz-tsv() {
  mkdir -p $BASE_DIR

  release-dirs \
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

  print-row \
    release_date version \
    osh_py_passing osh_cpp_passing ysh_py_passing ysh_cpp_passing

  while IFS=$'\t' read -a row; do
    local release_date=${row[0]}
    local version=${row[1]}
    local spec_wwz=${row[2]}
    local osh_py_path=${row[3]}
    local osh_cpp_path=${row[4]}
    local ysh_py_path=${row[5]}
    local ysh_cpp_path=${row[6]}

    if test $spec_wwz = '-'; then
      continue
    fi

    spec_wwz=$PWD/$spec_wwz

    local d=$base_dir/tmp/$version
    mkdir -p $d

    pushd $d > /dev/null

    # -o: overwrite without prompting

    local osh_py_passing='NA'
    if test $osh_py_path != '-'; then
      unzip -q -o $spec_wwz $osh_py_path
      osh_py_passing=$(osh-py-passing $osh_py_path)
    fi
    if test -z "$osh_py_passing"; then
      die "FAIL: osh_py_passing not extracted from $osh_py_path - $version $release_date"
    fi

    local osh_cpp_passing='NA'
    if test $osh_cpp_path != '-'; then
      unzip -q -o $spec_wwz $osh_cpp_path
      osh_cpp_passing=$(osh-cpp-passing $osh_cpp_path)
    fi
    if test -z "$osh_cpp_passing"; then
      die "FAIL: osh_cpp_passing not extracted from $osh_cpp_path - $version $release_date"
    fi

    local ysh_py_passing='NA'
    if test $ysh_py_path != '-'; then
      unzip -q -o $spec_wwz $ysh_py_path
      ysh_py_passing=$(ysh-py-passing $ysh_py_path)
    fi
    if test -z "$ysh_py_passing"; then
      die "FAIL: ysh_py_passing not extracted from $ysh_py_path - $version $release_date"
    fi

    local ysh_cpp_passing='NA'
    if test $ysh_cpp_path != '-'; then
      unzip -q -o $spec_wwz $ysh_cpp_path
      ysh_cpp_passing=$(ysh-cpp-passing $ysh_cpp_path)
    fi
    if test -z "$ysh_cpp_passing"; then
      die "FAIL: ysh_cpp_passing not extracted from $ysh_cpp_path - $version $release_date"
    fi

    popd > /dev/null

    print-row \
      "$release_date" "$version" \
      "$osh_py_passing" "$osh_cpp_passing" "$ysh_py_passing" "$ysh_cpp_passing"

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

  #log "path = $path"
  local name
  name=$(basename $path)

  # Heuristics for either index.html or osh.html

  if test "$name" = 'index.html'; then
    # It might be 3 or 5 -- I moved the columns around
    local count

    count=$(hxselect -s $'\n' -c 'tfoot td:nth-child(5)' < $path.xml)

    # Heuristic for differing format
    # TODO: This is bad.  Come up with something better.
    if test "$count" -lt 200; then
      count=$(hxselect -s $'\n' -c 'tfoot td:nth-child(3)' < $path.xml)
    fi
    echo "$count"

  else
    # survey/osh.html
    hxselect -s $'\n' -c '.totals:nth-child(1) td:nth-child(3)' < $path.xml | head -n 1
  fi
}

osh-cpp-passing() {
  ### Given a file, print the C++ total to stdout

  local path=$1
  normalize $path

  #echo "PATH $path"

  # Select the 2nd to last cell - this is more robust to format changes
  local cell
  cell=$(hxselect -s $'\n' -c '#summary thead tr:nth-child(2) td:nth-last-child(2)' < $path.xml)

  if test -z "$cell"; then
    # Oils 0.30.0 - changed to SUMMARY
    cell=$(hxselect -s $'\n' -c '#SUMMARY thead tr:nth-child(2) td:nth-last-child(2)' < $path.xml)
  fi

  # Change 1,137 -> 1137
  echo "$cell" | sed 's/,//'
}

ysh-py-passing() {
  ### Given a file, print the Python total to stdout

  local path=$1

  normalize $path

  local name
  name=$(basename $path)

  local count

  count=$(hxselect -s $'\n' -c 'tfoot td:nth-child(3)' < $path.xml)
  echo $count
}

ysh-cpp-passing() {
  ### Given a file, print the C++ total to stdout

  local path=$1
  # Same logic?
  osh-cpp-passing $path
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

make-plot() {
  devtools/release-history.R $BASE_DIR $BASE_DIR
}

copy() {
  cp -v $BASE_DIR/spec-test-history-2.png ../oilshell.org__deploy/blog/2022/03
}

deps-apt() { 
  # https://superuser.com/questions/528709/command-line-css-selector-tool
  sudo apt-get install html-xml-utils
}

# MEH these tools have bad error messages.
test-osh-py() {
  local test_dir=$BASE_DIR/test-parsing
  mkdir -p $test_dir

  # Show that's there
  #unzip -l $ROOT/release/0.9.8/test/spec.wwz || echo status=$?

  echo
  echo 'PYTHON 0.2.0'
  unzip -p $ROOT/release/0.2.0/test/spec.wwz 'index.html' > $test_dir/index.html
  osh-py-passing $test_dir/index.html

  echo
  echo 'PYTHON 0.7.pre3'
  unzip -p $ROOT/release/0.7.pre3/test/spec.wwz 'index.html' > $test_dir/index.html
  osh-py-passing $test_dir/index.html

  # hxnormalize makes it XML.
  # NOTE: syntax error on "<tr class=>", but it correctly ignores it
  echo
  echo 'PYTHON 0.9.8'
  # Annoying syntax for this command
  unzip -p $ROOT/release/0.9.8/test/spec.wwz 'survey/osh.html'  > $test_dir/osh.html
  osh-py-passing $test_dir/osh.html

  echo
  echo 'PYTHON 0.30.0'
  unzip -p $ROOT_OILS/release/0.30.0/test/spec.wwz 'osh-py/index.html' > $test_dir/index.html
  osh-py-passing $test_dir/index.html
}

test-osh-cpp() {
  local test_dir=$BASE_DIR/test-parsing
  mkdir -p $test_dir

  echo
  echo 'CPP 0.9.8'
  unzip -p $ROOT/release/0.9.8/test/spec.wwz 'cpp/osh-summary.html' > $test_dir/osh-summary.html
  osh-cpp-passing $test_dir/osh-summary.html 

  # May 2026: updating the 2022 graph
  echo 'CPP 0.19.0'
  unzip -p $ROOT/release/0.19.0/test/spec.wwz 'osh-cpp/compare.html' > $test_dir/compare.html
  osh-cpp-passing $test_dir/compare.html

  echo 'CPP 0.30.0'
  unzip -p $ROOT_OILS/release/0.30.0/test/spec.wwz 'osh-cpp/compare.html' > $test_dir/compare.html
  osh-cpp-passing $test_dir/compare.html
}

test-ysh-py() {
  local test_dir=$BASE_DIR/test-parsing
  mkdir -p $test_dir

  echo
  echo 'YSH PY 0.9.8'
  unzip -p $ROOT/release/0.9.8/test/spec.wwz 'oil-language/oil.html' > $test_dir/oil.html
  ysh-py-passing $test_dir/oil.html 

  echo
  echo 'YSH PY 0.30.0'
  unzip -p $ROOT_OILS/release/0.30.0/test/spec.wwz 'ysh-py/index.html' > $test_dir/index.html
  ysh-py-passing $test_dir/index.html
}

test-ysh-cc() {
  local test_dir=$BASE_DIR/test-parsing
  mkdir -p $test_dir

  echo
  echo 'YSH CC 0.30.0'
  unzip -p $ROOT_OILS/release/0.30.0/test/spec.wwz 'ysh-cpp/compare.html' > $test_dir/compare.html
  ysh-cpp-passing $test_dir/compare.html
}

do-all() {
  wwz-tsv
  spec-tsv
  make-plot
}

"$@"
