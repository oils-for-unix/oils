#!/bin/bash
#
# Usage:
#   ./doc.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

#
# TODO: Use this 2017 release!
# 
# http://www.html-tidy.org/
# http://binaries.html-tidy.org/
#
# The Ubuntu version is from 2009!

validate-html() {
  # -e shows only errors
  # -q suppresses other text

  echo
  echo "--- $1"
  echo

  set +o errexit
  tidy -e -q -utf8 "$@"
  local status=$?

  if test $status -ne 0; then
    #exit 255  # stop xargs
    return $status
  fi
}

manifest() {
  local -a html_dirs=(
    _release/VERSION 
    _tmp/unit
    #_tmp/spec
    _tmp/osh-parser

    #_tmp/test-opy _tmp/metrics \ 
  )
  # There are a lot of empty <pre></pre> here which I don't care about
  # _tmp/spec \
  # 
  # things I don't care about:
  # - empty <pre> resulting from auto-generated code
  # - proprietary attributes -- I use some, doesn't understand "col"

  find "${html_dirs[@]}" -name '*.html' 
}

release-tree() {
  ### Lint SOME of the release tree

  manifest | xargs -n 1 --verbose -- $0 validate-html
}

# A tree of files to test.

# Note: you also need to look at the originals in _tmp/unit, etc. because most
# of these are compressed.

quickly-build-release-tree() {
  test/unit.sh write-report
  test/wild-runner.sh make-report

  local suite='osh'
  local manifest=_tmp/spec/SUITE-$suite.txt

  test/spec-runner.sh all-tests-to-html $manifest
  test/spec-runner.sh html-summary $suite

  local version=0.7.pre10

  devtools/release-version.sh git-changelog-$version
  devtools/release-version.sh announcement-$version

  benchmarks/report.sh all

  devtools/release.sh build-tree

  # gah this builds .wwz files
  # but it shows you all the locations where they live
  devtools/release.sh compress

  # Now to ./local.sh test-release-tree to upload _release/VERSION to the
  # server
}

"$@"
