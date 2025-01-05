#!/usr/bin/env bash
#
# The big Oils release process.
#
# Usage:
#   devtools/release.sh <function name>
#
# Steps:
#   edit oils-version.txt, build/doc.sh update-src-versions, and
#     bump devtools/release-note.sh
#   $0 make-release-branch
#   $0 two-tarballs          # CPython, then oils-for-unix, which is INSTALLED
#   demo/osh-debug.sh osh-for-release: Start a shell to dogfood
#   build/cpython-defs.sh {oil-py-names,filter-methods}
#     (regenerate C source)
#
# Run on each machine:
#   $0 auto-machine1
#   $0 auto-machine2 ($0 dep-benchmarks first)
#
# In between:
#   [switch benchmarks-data repo] commit src/oil-for-unix-* and push to flanders.
#   TODO: Make sure benchmark-data directory is clean!
#
# Resume manual work
#
#   Commit files to oilshell/benchmark-data repo and sync.
#   benchmarks/report.sh all
#   $0 deploy-tar  # needed to publish tarball checksum in HTML
#   build/doc.sh run-for-release
#   $0 compress
#   devtools/release-version.sh git-changelog-$VERSION
#   devtools/release-version.sh announcement-$VERSION
#   MAYBE: ./local.sh test-release-tree if you want to preview it
#   $0 deploy-doc (makes releases.html)
#
#   demo/osh-debug.sh analyze  # see what you ran
# 
# - Go to oils.pub repo and do:
#   ./deploy.sh site                  # copy release
#   ./deploy.sh bump-index-version
#   make
#   ./deploy.sh site                  # copy new index
#   ./deploy.sh bump-release-version
# - Go to oils.pub__deploy and "git add release/$VERSION".
#   - git commit -a

set -o nounset
set -o pipefail
set -o errexit

shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

REPO_ROOT=$(cd $(dirname $0)/.. ; pwd)
OIL_VERSION=$(head -n 1 oils-version.txt)

source devtools/common.sh  # banner
source benchmarks/common.sh  # BENCHMARK_DATA_OILS, OSH_CPP_BENCHMARK_DATA
                             # redefines OIL_VERSION as readonly

readonly OSH_RELEASE_BINARY=$REPO_ROOT/_tmp/oil-tar-test/oil-$OIL_VERSION/_bin/osh
readonly YSH_RELEASE_BINARY=$REPO_ROOT/_tmp/oil-tar-test/oil-$OIL_VERSION/_bin/ysh

log() {
  echo "$@" 1>&2
}

make-release-branch() {
  git checkout master
  local name=release/$OIL_VERSION
  git checkout -b $name
  git push -u origin $name
}

ensure-smooth-build() {
  # Stray files can mess up the unit tests
  devtools/git.sh error-if-untracked

  build/clean.sh

  sudo -k; sudo true  # clear and re-cache credentials

  # Install with root privileges
  _install
}

# For redoing a release.  This is everything until you have to 'git pull' the
# benchmark-data repo to make reports.
#
# PRECONDITION: $0 two-tarballs was run manually, which runs
# ensure-smooth-build.
auto-machine1() {
  local resume=${1:-}  # workaround for spec test flakiness bug
  local resume2=${2:-}  # skip past spec sanity check
  local resume3=${3:-}  # skip past metrics and wild tests
  local resume4=${4:-}  # skip past full spec tests

  if test -z "$resume"; then
    $0 build-and-test
  fi 

  if test -z "$resume2"; then
    _spec-sanity-check  # just run a few spec tests
  fi

  if test -z "$resume3"; then
    $0 metrics  # this can catch bugs
    test/wild.sh all
  fi

  if test -z "$resume4"; then
    $0 spec-all  # full spec test run
  fi

  $0 benchmark-run do_machine1
}

# Note: needs dep-benchmarks to run
auto-machine2() {
  ensure-smooth-build

  # Note: this can't be done until we sync the oils-for-unix source from
  # machine 1.
  $0 benchmark-build
  $0 benchmark-run
}

# TODO:
# - enforce that there is a release/$VERSION branch?

# oils.pub__deploy/
#   releases.html
#   release/
#     $VERSION/
#       index.html  # release page, from doc/release-index.md
#       oils-version.txt
#       release-date.txt
#       announcement.html  # HTML redirect
#       changelog.html
#       doc/
#         index.html
#         ...
#       test/  # results
#         spec.wwz/
#           machine-lisa/
#         wild.wwz/
#         unit.wwz/
#         other.wwz/
#           gold.txt
#           parse-errors.txt
#           runtime-errors.txt
#           tools-deps.txt
#           osh-usage.txt
#           lossless.txt
#         tarball/  # log of building and running the tarball?
#       asan/       # spec tests or other?
#                   # or it can be put under test/{spec,wild}
#       metrics.wwz/  # static metrics on source code?
#         line-counts/
#           nativedeps.txt (build/stats.sh line counts)
#         bytecode size, number of PyCodeObject
#         number of functions, classes, etc.?
#         bytecode/bundle size (binary size on x86_64 is in ovm-build.sh)
#         tarball size?
#       coverage.wwz/
#         unified/   # clang-coverage
#       benchmarks.wwz/
#         compute
#         osh-parser/
#         osh-runtime/
#         vm-baseline/
#         ...
#         startup/
#   download/  # What about native binaries?
#     0.0.0/  
#       oil-0.0.0.tar.xz 

_test-tarball() {
  local name=${1:-hello}
  local version=${2:-0.0.0}
  local install=${3:-}

  local tmp=_tmp/${name}-tar-test
  rm -r -f $tmp
  mkdir -p $tmp

  pushd $tmp
  tar --extract -z < ../../_release/$name-$version.tar.gz

  cd $name-$version
  ./configure

  # Build the fast one for a test.
  # TODO: Maybe edit the Makefile to change the top target.
  local bin=_bin/${name}.ovm  # not dbg
  time make $bin
  $bin --version

  if test -n "$install"; then
    sudo ./install
  fi
  popd
}

test-oil-tar() {
  local install=${1:-}  # non-empty to install
  _test-tarball oil $(head -n 1 oils-version.txt) "$install"
}

_release-build() {
  # NOTE: deps/from-tar.sh {configure,build}-python is assumed

  # Build the oil tar
  $0 oil

  test-oil-tar

  # For _spec-sanity-check
  ln -s -f --no-target-directory -v oil.ovm $OSH_RELEASE_BINARY
  ln -s -f --no-target-directory -v oil.ovm $YSH_RELEASE_BINARY
}

readonly HAVE_ROOT=1

readonly -a MORE_TESTS=(
  process-table
  gold 
  ysh-ify
  parse-errors runtime-errors
  ysh-runtime-errors
  ysh-parse-errors
  ysh-every-string
  lossless
  osh-usage tools-deps
  syscall
)
# TODO: Unify with CI, and clean up
# doc/error-catalog.sh
# data_lang/j8-errors.sh
# ysh/run.sh

run-more-tests() {
  for name in "${MORE_TESTS[@]}"; do
    case $name in
      gold)
        if test -n "${OILS_HIJACK_SHEBANG:-}"; then
          cat >&2 <<'EOF'
=====
WARNING: Skipping gold tests because $OILS_HIJACK_SHEBANG is set.'
Run them manually with:

  test/gold.sh run-for-release
=====
EOF
          continue
        fi
        ;;
      *)
        banner "Test suite: $name"
        ;;
    esac

    test/$name.sh run-for-release
  done

  ysh/run.sh run-for-release

  data_lang/j8-errors.sh run-for-release
}

_spec-sanity-check() {
  # Quick early test for _bin/osh and _bin/ysh

  # TODO: Use --ovm-bin-dir
  # Note: MAX_PROCS=1 prevents [#oil-dev > Random Spec Test Stoppages]
  # Still need to fix that bug
  MAX_PROCS=1 NUM_SPEC_TASKS=2 OSH_LIST="$OSH_RELEASE_BINARY" test/spec-py.sh osh-all
  MAX_PROCS=1 NUM_SPEC_TASKS=2 YSH_LIST="$YSH_RELEASE_BINARY" test/spec-py.sh ysh-all
}

spec-all() {
  ### Run all spec tests

  test/stateful.sh soil-run  # Same as CI

  # Create the tests we're running
  test/smoosh.sh make-spec

  # TODO: Use --ovm-bin-dir
  export OSH_LIST="$REPO_ROOT/bin/osh $OSH_RELEASE_BINARY"
  export YSH_LIST="$REPO_ROOT/bin/ysh $YSH_RELEASE_BINARY"
  test/spec-py.sh all-and-smoosh

  # Build $OSH_CPP_BENCHMARK_DATA
  _build-oils-benchmark-data

  # TODO: Use --oils-cpp-bin-dir
  # Collect and publish stats about the C++ translation.
  OSH_CC="$OSH_CPP_BENCHMARK_DATA" test/spec-cpp.sh osh-all
  YSH_CC="$YSH_CPP_BENCHMARK_DATA" test/spec-cpp.sh ysh-all
}

spec-cpp() {
  ### For repair

  # TODO: Use --oils-cpp-bin-dir

  # Quick
  # NUM_SPEC_TASKS=2 OSH_CC="$OSH_CPP_BENCHMARK_DATA" test/spec-cpp.sh all
  OSH_CC="$OSH_CPP_BENCHMARK_DATA" test/spec-cpp.sh all
}

# For quickly debugging failures that don't happen in dev mode.
spec-one() {
  export OSH_LIST="$REPO_ROOT/bin/osh $OSH_RELEASE_BINARY"
  export YSH_LIST="$REPO_ROOT/bin/ysh $YSH_RELEASE_BINARY"
  test/spec.sh "$@"
}

build-and-test() {
  ### Build tarballs and test them.  And preliminaries like unit tests.

  # TODO: Log this whole thing?  Include logs with the /release/ page?

  # Before doing anything
  test/lint.sh soil-run

  test/unit.sh run-for-release  # Python unit tests

  test/coverage.sh run-for-release  # C++ unit tests

  # App bundle
  _release-build

  # TODO: test oils-for-unix in Alpine chroot too.
  # NOTE: Need test/alpine.sh download;extract;setup-dns,add-oil-build-deps,
  # etc.
  if test -n "$HAVE_ROOT"; then
    # TODO: Factor out test/alpine.sh to test/chroot.sh
    test/alpine.sh copy-tar '' oil
    test/alpine.sh test-tar '' oil
  fi

  test/spec.sh smoke  # Initial smoke test, slightly redundant.

  run-more-tests
}

_install() {
  test/spec-bin.sh install-shells-with-apt

  # A subset of build/py.sh ubuntu-deps.  (Do we need build-essential?)
  #sudo apt install python-dev
}

_build-oils-benchmark-data() {
  pushd $BENCHMARK_DATA_OILS
  ./configure
  for variant in dbg opt; do
    # DWARF version 4 is a hack for bloaty, which doesn't support version 5.
    # I don't think this should affect benchmarks besides
    # metrics/native-code.sh, so we don't bother building a separate binary.
    # The Soil CI runs without this flag.
    CXXFLAGS=-gdwarf-4 _build/oils.sh --variant "$variant" --skip-rebuild
  done
  popd
}

benchmark-build() {
  ### Build function on machine 2.

  build/clean.sh
  if test -n "$HAVE_ROOT"; then
    _install
  fi
  build/py.sh all
  _release-build
}

# Run benchmarks with the binary built out of the tarball.
benchmark-run() {
  local do_machine1=${1:-}

  _build-oils-benchmark-data
  OSH_OVM=$OSH_RELEASE_BINARY benchmarks/auto.sh all "$do_machine1"
}

_compressed-tarball() {
  local name=${1:-hello}
  local version=${2:-0.0.0}

  local in=_release/$name.tar
  local out=_release/$name-$version.tar.gz

  # Overwrite it to cause rebuild of oil.tar
  build/stamp.sh write-release-date

  #make -d -r $in  # To debug
  make $in
  time gzip -c $in > $out
  ls -l $out

  # xz version is considerably smaller.  1.15 MB  vs. 1.59 MB.
  local out2=_release/$name-$version.tar.xz
  time xz -c $in > $out2
  ls -l $out2
}

oil() {
  _compressed-tarball oil $OIL_VERSION
}

hello() {
  _compressed-tarball hello $(head -n 1 build/testdata/hello-version.txt)
}


_link() {
  ln -s -f -v --no-target-directory "$@"
}

compress() {
  local root=$PWD/_release/VERSION/

  log '--- more-tests'
  local out="$root/more-tests.wwz"
  pushd _tmp
  time zip -r -q $out suite-logs unit syscall process-table
  popd

  # This has HTML reports, .profraw files, and logs of stdout, e.g.
  # mycpp-unit/gc_heap_test.log
  # About 1.5 MB
  log "--- coverage"
  local out="$root/test/coverage.wwz"
  pushd _test/clang-coverage
  # This also saves the logs
  time zip -r -q $out .
  popd

  log "--- test/spec"
  local out="$root/test/spec.wwz"
  pushd _tmp/spec
  time zip -r -q $out .  # recursive, quiet
  popd

  log "--- test/wild"
  local out="$root/test/wild.wwz"
  pushd _tmp/wild-www
  time zip -r -q $out .  # recursive, quiet
  popd

  # NOTE: must be /pub/metrics.wwz so that relative URLs like
  # ../../../web/line-counts.css work.  The Soil UI also relies on such
  # relative URLs.
  log "--- metrics"
  local out="$root/pub/metrics.wwz"
  pushd _tmp/metrics
  time zip -r -q $out .  # recursive, quiet
  popd

  # Ditto: pub/src-tree.wwz lines up with URLs in Soil
  log "--- src-tree"
  local out="$root/pub/src-tree.wwz"
  pushd _tmp/src-tree-www
  time zip -r -q $out .  # recursive, quiet
  popd

  compress-benchmarks

  tree _release/VERSION
}

compress-benchmarks() {
  local root=$PWD/_release/VERSION/
  mkdir -p $root

  log "--- benchmarks"

  local out="$root/benchmarks.wwz"

  # - For benchmarks that run on multiple machines, technically we only need
  #   index.html, but include stage1 and stage2.
  # - For those that run on single machines, we also archive the raw/ dir.
  #   - Although benchmarks/compute is saved in oilshell/benchmark-data
  # - Note: _tmp/uftrace/{raw,stage1} are big (hundreds of MB), so leave them
  #   out

  pushd _tmp
  find \
    osh-parser/{stage1,stage2,index.html} \
    osh-runtime/{stage1,stage2,index.html} \
    vm-baseline/{stage1,stage2,index.html} \
    ovm-build/{stage1,stage2,index.html} \
    compute/{raw,stage1,stage2,index.html} \
    gc/{raw,stage2,index.html} \
    gc-cachegrind/{raw,stage2,index.html} \
    mycpp-examples/{raw,stage2,index.html} \
    uftrace/{stage2,index.html} \
    -type f \
    | xargs --verbose -- zip -q $out 
  popd
}

line-counts() {
  local out_dir=$1  # should be an absolute path
  mkdir -p $out_dir

  # Counting directly from the build.
  metrics/tarball.sh linecount-pydeps > $out_dir/pydeps.txt
  metrics/tarball.sh linecount-nativedeps > $out_dir/nativedeps.txt
  metrics/tarball.sh linecount-oils-cpp > $out_dir/oils-cpp.txt

  metrics/source-code.sh write-reports $out_dir  # for-translation and overview
  metrics/source-code.sh cloc-report > $out_dir/cloc-report.txt

  # goes to _tmp/metrics/preprocessed
  metrics/source-code.sh preprocessed
}

metrics() {
  local out=_tmp/metrics
  mkdir -p $out

  line-counts $PWD/$out/line-counts

  # For another .wwz file
  doctools/src-tree.sh soil-run

  metrics/bytecode.sh run-for-release
  metrics/native-code.sh run-for-release
  # Disabled 2024-12
  # build/cpython-defs.sh run-for-release

  tree $out
}

deploy-doc() {
  local deploy_repo='../oils.pub__deploy'
  local release_root_dir="$deploy_repo/release"
  local release_dir="$release_root_dir/$OIL_VERSION"

  mkdir -p $release_dir
  cp -v -r --force --no-target-directory \
    _release/VERSION/ $release_dir/

  # Generate release index.
  html-index $release_root_dir _tmp/releases.html
  cp -v _tmp/releases.html $deploy_repo

  tree -L 3 $release_root_dir
  
  ls -l $deploy_repo/releases.html
}

readonly DOWNLOAD_DIR='../oils.pub__deploy/download/'

# Generating releases.html requires the old tarballs!
sync-old-tar() {
  local user=$1  # required username
  rsync --archive --verbose \
    $user@oilshell.org:oilshell.org/download/ $DOWNLOAD_DIR
}

# I think these aren't checked into git?  They can just be managed separately?
# Or should you check in the sha checksums?  Those will be in releases.html,
# but a CSV might be nice.
deploy-tar() {
  mkdir -p $DOWNLOAD_DIR

  cp -v \
    _release/oil-$OIL_VERSION.tar.* _release/oils-for-unix-$OIL_VERSION.tar.* \
    $DOWNLOAD_DIR

  ls -l $DOWNLOAD_DIR
}

#
# Generate releases.html.
#

# Examples of similar release HTML pages:
# - https://golang.org/dl/  -  "Older versions", sha1 / sha256.
# - Python has all point releases in chronological order, and then a separate
# page for each changelog.  There is too much boilerplate maybe?
#   - It has release notes before the downloads.  Not sure I like that.
# - node.js: https://nodejs.org/en/
#   - user agent detection for the right binary -- meh I don't want that
# - Ruby: https://www.ruby-lang.org/en/downloads/releases/
# - https://www.lua.org/download.html

# Columns: Date / Version / Docs /    / Files
#                           Changelog  .xz
#                           Install
#                           Docs/
#
# The files could be a separate page and separate table?  I could provide
# pre-built versions eventually?  Linux static versions?

# TODO: Each of these would be a good candidate for a data frame!  Data vs.
# presentation.

# Simple UI:
# - home page shows latest version (source release for now, binary release later?)
#   - link to Changelog, INSTALL, doc index
# - or see all releases
# - Grey out older releases?

# TODO: Should be sorted by date?  How to do that, with bash array?  Or Awk?
# $timestamp $version $timestamp file?  And then sort -n  I guess?  Change
# the release date format.  It will use Unix timestamp (OK until 2038!)

_html-index() {
  local release_root_dir=$1 # the directory we want to make an index of

  for entry in $release_root_dir/*; do
    if ! test -d $entry; then
      continue
    fi
    local dir=$entry

    local version
    version=$(head -n 1 $dir/oils-version.txt)
    local release_date
    release_date=$(head -n 1 $dir/release-date.txt)

    log "-- $dir"
    log "Version: $version"
    log "Release Date: $release_date"
    log ""

    echo "$release_date $version"
  done > _tmp/release-meta.txt

  # Reverse sort by release date
  sort -r _tmp/release-meta.txt > _tmp/sorted-releases.txt

  while read date _ version; do
    log "Release Date: $date"
    log "Version: $version"

    # anchor
    cat <<EOF
<tr>
  <td>
    <span class="date">$date</span>
  </td>
  <td>
    <a name="$version"></a>
    <span class="version-number">$version</span>
  </td>
  <td>
    <p>                <a href="release/$version/announcement.html">Announcement</a>
       &nbsp; | &nbsp; <a href="release/$version/">Docs and Details</a>
    </p>
  </td>
</tr>
EOF

    build/doc.sh tarball-links-row-html $version

    cat <<EOF
<tr>
  <td colspan="3">
    <div style="padding: 1em;" >
    </div>
  </td>
</tr>

EOF

  done < _tmp/sorted-releases.txt
}

_releases-html-header() {
  # TODO: use html-head here, and publish web/*.css somewhere outside of
  # /release/$VERSION/?  The list of all releases isn't versioned for obvious
  # reasons.  Other docs are in the oilshell.org repo using the all-2020.css
  # bundle.

  cat <<EOF
<!DOCTYPE html>
<html>
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Oils Releases</title>
    <style>
EOF

  cat web/base.css
  cat web/release-index.css

cat <<EOF
      h1 {
        text-align: center;
      }
    </style>
  </head>
  <body class="width50">
    <p id="home-link">
      <a href="/">oils.pub</a>
    </p>
    <h1>Oils Releases</h1>

    <table class="release-table">
EOF
}

html-index() {
  local release_root_dir=$1
  local out=${2:-_tmp/releases.html}

  { _releases-html-header
    _html-index $release_root_dir

    cat <<EOF
    </table>
  </body>
</html>
EOF

  } > $out

  ls -l $out
}

# For quickly iterating on tarball size reductions.
tarball-size() {
  make clean-repo
  make _bin/oil.ovm-dbg  # faster way to build bytecode
  oil  # make tarball
  test-oil-tar  # Ctrl-C this, then run metrics/tarball.sh
}

dep-smoosh() {
  local repo=~/git/languages/smoosh
  if ! test -d $repo; then
    local base_dir=$(dirname $repo)
    mkdir -p $base_dir
    pushd $base_dir
    git clone git@github.com:mgree/smoosh.git
    popd
  fi
}

dep-benchmarks() {
  ### Before auto-machine2

  # 2023-07: Also need deps/from-tar.sh {configure,build}-cpython

  benchmarks/osh-runtime.sh download
  benchmarks/osh-runtime.sh extract

  benchmarks/ovm-build.sh download
  benchmarks/ovm-build.sh extract-other

  # For ovm-build benchmark.
  deps/from-binary.sh download-clang
  deps/from-binary.sh extract-clang
}

more-release-deps() {
  # List of deps that are NOT in soil/worker.sh here
  # https://github.com/oilshell/oil/issues/926

  # TODO: Make a container image for these.
  if false; then
    # TODO: Did this manually
    # test/alpine.sh
    # dep-alpine

    # test/smoosh.sh
    dep-smoosh

    dep-benchmarks
  fi
}

py-tarball() {
  local in=_release/oil.tar
  local out=_release/oil-$OIL_VERSION.tar.gz

  make $in
  time gzip -c $in > $out
  ls -l $out

  test-oil-tar
}

native-tarball() {
  # oils-for-unix
  devtools/release-native.sh make-tar
  # Also install as root
  devtools/release-native.sh extract-for-benchmarks INSTALL
}

two-tarballs() {
  ### First step of release.  Assume that CI passes

  ensure-smooth-build

  build/py.sh all
  # "Base state" for repo scripts
  ./NINJA-config.sh

  py-tarball

  native-tarball
}

upload-tmp() {
  local tarball=$1
  local user=$2

  scp $tarball $user@oilshell.org:tmp/
}

sync-tmp() {
  local user=$1
  local dest=${2:-_tmp/candidates}
  mkdir -p $dest
  rsync --archive --verbose $user@oilshell.org:tmp/ $dest
}

"$@"
