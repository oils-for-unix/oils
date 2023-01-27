#!/usr/bin/env bash
#
# The big Oil release process.
#
# Usage:
#   devtools/release.sh <function name>
#
# Steps:
#   edit oil-version.txt and build/doc.sh update-src-versions
#   $0 make-release-branch
#   build/py.sh yajl-release
#   $0 quick-oil-tarball     # build FIRST tarball
#   $0 test-oil-tar T        # extract, build, install
#                            # for cpython-defs source scanning and dogfood
#   demo/osh-debug.sh osh-for-release: Start a shell to dogfood
#   build/cpython-defs.sh {oil-py-names,filter-methods}
#     (regenerate C source)
#
# Run on each machine:
#   $0 auto-machine1
#   $0 auto-machine2
#
# In between:
#   [switch benchmarks-data repo] commit src/oil-for-unix-* and push to flanders.
#   TODO: Make sure benchmark-data directory is clean!
#
# Resume manual work
#
#   Commit files to oilshell/benchmark-data repo and sync.
#   benchmarks/report.sh all
#   $0 deploy-tar  # needed to checksum
#   $0 build-tree
#   $0 compress
#   devtools/release-version.sh git-changelog-$VERSION
#   devtools/release-version.sh announcement-$VERSION
#   MAYBE: ./local.sh test-release-tree if you want to preview it
#   $0 deploy-doc (makes releases.html)
#
#   demo/osh-debug.sh analyze  # see what you ran
# 
# - Go to oilshell.org repo and do:
#   ./deploy.sh site                  # copy release
#   ./deploy.sh bump-index-version
#   make
#   ./deploy.sh site                  # copy new index
#   ./deploy.sh bump-release-version
# - Go to oilshell.org__deploy and "git add release/$VERSION".
#   - git commit -a

set -o nounset
set -o pipefail
set -o errexit

shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

REPO_ROOT=$(cd $(dirname $0)/.. ; pwd)
OIL_VERSION=$(head -n 1 oil-version.txt)

source devtools/common.sh  # banner
source benchmarks/common.sh  # BENCHMARK_DATA_OILS, OSH_CPP_BENCHMARK_DATA
                             # redefines OIL_VERSION as readonly

readonly OSH_RELEASE_BINARY=$REPO_ROOT/_tmp/oil-tar-test/oil-$OIL_VERSION/_bin/osh
readonly OIL_RELEASE_BINARY=$REPO_ROOT/_tmp/oil-tar-test/oil-$OIL_VERSION/_bin/oil

log() {
  echo "$@" 1>&2
}

make-release-branch() {
  git checkout master
  local name=release/$OIL_VERSION
  git checkout -b $name
  git push -u origin $name
}

# For redoing a release.  This is everything until you have to 'git pull' the
# benchmark-data repo to make reports.
auto-machine1() {
  local resume=${1:-}  # workaround for spec test flakiness bug
  local resume2=${2:-}  # skip past metrics and wild tests

  sudo -k; sudo true  # clear and re-cache credentials

  if test -z "$resume"; then
    # Note: spec tests run here
    # _test-release-build -> _spec-release
    $0 build-and-test
  fi 

  if test -z "$resume2"; then
    $0 metrics  # this can catch bugs
    test/wild.sh all
  fi

  $0 spec-all  # spec tests run here again
  $0 benchmark-run do_machine1
}

# Note: needs dep-benchmarks to run
auto-machine2() {
  sudo -k; sudo true  # clear and re-cache credentials

  # Note: this can't be done until we sync the oils-for-unix source from
  # machine 1.
  $0 benchmark-build
  $0 benchmark-run
}

# TODO:
# - enforce that there is a release/$VERSION branch?

# oilshell.org__deploy/
#   releases.html
#   release/
#     $VERSION/
#       index.html  # release page, from doc/release-index.md
#       oil-version.txt
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
#           oshc-deps.txt
#           osh-usage.txt
#           arena.txt
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
  _test-tarball oil $(head -n 1 oil-version.txt) "$install"
}

_release-build() {
  # NOTE: deps/from-tar.sh {configre,build}-python is assumed

  # Build the oil tar
  $0 oil

  test-oil-tar

  ln -s -f --no-target-directory -v oil.ovm $OSH_RELEASE_BINARY
  ln -s -f --no-target-directory -v oil.ovm $OIL_RELEASE_BINARY
}

readonly HAVE_ROOT=1

readonly -a OTHER_TESTS=(
  gold 
  ysh-prettify
  parse-errors runtime-errors
  oil-runtime-errors
  arena
  osh-usage oshc-deps
  syscall
)

run-other-tests() {
  for name in "${OTHER_TESTS[@]}"; do
    case $name in
      gold)
        if test -n "${OSH_HIJACK_SHEBANG:-}"; then
          cat >&2 <<'EOF'
=====
WARNING: Skipping gold tests because $OSH_HIJACK_SHEBANG is set.'
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

  oil_lang/run.sh run-for-release
  tea/run.sh run-for-release
}

_spec-release() {
  # Just test the release build (as opposed to Oil under CPython, which comes
  # later.)
  export OSH_LIST="$OSH_RELEASE_BINARY" OIL_LIST="$OIL_RELEASE_BINARY"
  test/spec.sh osh-all
  test/spec.sh oil-all

  # Eventually we should run spec tests against the oils-for-unix tarball here
}

_test-release-build() {
  # NOTE: Need test/alpine.sh download;extract;setup-dns,add-oil-build-deps,
  # etc.

  if test -n "$HAVE_ROOT"; then
    # TODO: Factor out test/alpine.sh to test/chroot.sh
    test/alpine.sh copy-tar '' oil
    test/alpine.sh test-tar '' oil
  fi

  test/spec.sh smoke  # Initial smoke test, slightly redundant.

  run-other-tests

  _spec-release
}

spec-all() {
  ### Run all spec tests

  test/stateful.sh soil-run  # Same as CI

  # Create the tests we're running
  test/smoosh.sh make-spec

  # 8/2019: Added smoosh
  export OSH_LIST="$REPO_ROOT/bin/osh $OSH_RELEASE_BINARY"
  export OIL_LIST="$REPO_ROOT/bin/oil $OIL_RELEASE_BINARY"
  test/spec.sh all-and-smoosh

  # Build $OSH_CPP_BENCHMARK_DATA
  _build-oils-benchmark-data

  # Collect and publish stats about the C++ translation.
  OSH_CC="$OSH_CPP_BENCHMARK_DATA" test/spec-cpp.sh all
}

# For quickly debugging failures that don't happen in dev mode.
spec-one() {
  export OSH_LIST="$REPO_ROOT/bin/osh $OSH_RELEASE_BINARY"
  export OIL_LIST="$REPO_ROOT/bin/oil $OIL_RELEASE_BINARY"
  test/spec.sh "$@"
}

build-and-test() {
  ### Build tarballs and test them.  And preliminaries like unit tests.

  # TODO: Log this whole thing?  Include logs with the /release/ page?

  # Before doing anything
  test/lint.sh soil-run

  build/clean.sh
  build/py.sh all
  test/unit.sh run-for-release  # Python unit tests

  # "Base state" for repo scripts
  ./NINJA-config.sh

  test/coverage.sh run-for-release  # C++ unit tests

  # oils-for-unix
  devtools/release-native.sh make-tar
  devtools/release-native.sh extract-for-benchmarks
  # This builds the tarball from _tmp/native-tar-test
  devtools/release-native.sh test-tar

  # App bundle
  _release-build
  _test-release-build  # Note: spec tests run here
}

_install() {
  test/spec.sh install-shells-with-apt

  # A subset of build/py.sh ubuntu-deps.  (Do we need build-essential?)
  sudo apt install python-dev
}

_build-oils-benchmark-data() {
  pushd $BENCHMARK_DATA_OILS
  _build/oils.sh '' opt SKIP_REBUILD
  _build/oils.sh '' dbg SKIP_REBUILD  # for metrics/native-code.sh
  popd
}

benchmark-build() {
  ### Build function on machine 2.

  if test -n "$HAVE_ROOT"; then
    _install
  fi
  build/clean.sh
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
  build/ovm-actions.sh write-release-date

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

  # This has HTML reports, .profraw files, and logs of stdout, e.g.
  # mycpp-unit/gc_heap_test.log
  # About 1.5 MB
  log "--- coverage"
  local out="$root/test/coverage.wwz"
  pushd _test/clang-coverage
  # This also saves the logs
  time zip -r -q $out .
  popd

  log "--- test/other"
  local out="$root/test/other.wwz"
  pushd _tmp/other
  time zip -r -q $out .  # recursive, quiet
  popd

  log "--- test/unit"
  local out="$root/test/unit.wwz"
  pushd _tmp/unit
  time zip -r -q $out .  # recursive, quiet
  popd

  log "--- test/spec"
  local out="$root/test/spec.wwz"
  pushd _tmp/spec
  time zip -r -q $out .  # recursive, quiet
  popd

  log "--- test/wild"
  local out="$root/test/wild.wwz"
  pushd _tmp/wild/www
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

  log "--- source-code"
  local out="$root/source-code.wwz"
  pushd _tmp/important-source-code
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

  pushd _tmp
  find \
    osh-parser/{stage1,stage2,index.html} \
    osh-runtime/{stage1,stage2,index.html} \
    vm-baseline/{stage1,stage2,index.html} \
    ovm-build/{stage1,stage2,index.html} \
    compute/{raw,stage1,stage2,index.html} \
    gc/{raw,stage2,index.html} \
    mycpp-examples/{raw,stage2,index.html} \
    -type f \
    | xargs --verbose -- zip -q $out 
  popd
}

line-counts() {
  local out=$1  # should be an absolute path
  mkdir -p $out

  # Counting directly from the build.
  metrics/tarball.sh linecount-pydeps > $out/pydeps.txt
  metrics/tarball.sh linecount-nativedeps > $out/nativedeps.txt
  metrics/tarball.sh linecount-oil-cpp > $out/oil-cpp.txt

  metrics/source-code.sh write-reports  # for-translation and overview
  metrics/source-code.sh osh-cloc > $out/osh-cloc.txt

  # goes to _tmp/metrics/preprocessed
  metrics/source-code.sh preprocessed
}

metrics() {
  local out=_tmp/metrics
  mkdir -p $out

  line-counts $PWD/$out/line-counts

  metrics/bytecode.sh run-for-release
  metrics/native-code.sh run-for-release
  build/cpython-defs.sh run-for-release

  # For another .wwz file
  build/doc.sh important-source-code

  tree $out
}

_copy-path() {
  local src=$1 dest=$2
  mkdir -p $(dirname $dest)
  cp -v $src $dest
}

copy-web() {
  find web \
    \( -name _tmp -a -prune \) -o \
    \( -name '*.css' -o -name '*.js' \) -a -printf '%p _release/VERSION/%p\n' |
  xargs -n 2 -- $0 _copy-path
}

this-release-links() {
  echo '<div class="file-table">'
  echo '<table>'
  _tarball-links-row-html "$OIL_VERSION"
  echo '</table>'
  echo '</div>'
}

# Turn HTML comment into a download link
add-date-and-links() {
  awk -v date=$1 -v snippet="$(this-release-links)" '
    /<!-- REPLACE_WITH_DOWNLOAD_LINKS -->/ {
      print(snippet)
      next
    }

    /<!-- REPLACE_WITH_DATE -->/ {
      print(date)
      next
    }

    # Everything else
    { print }
  '
}

modify-pages() {
  local release_date
  release_date=$(cat _build/release-date.txt)

  local root=_release/VERSION

  add-date-and-links $release_date < _tmp/release-index.html > $root/index.html
  add-date-and-links $release_date < _tmp/release-quality.html > $root/quality.html
}

build-tree() {
  local root=_release/VERSION
  mkdir -p $root/{doc,test,pub}

  # Metadata
  cp -v _build/release-date.txt oil-version.txt $root

  # Docs
  # Writes _release/VERSION and _tmp/release-index.html
  build/doc.sh run-for-release

  modify-pages

  # Problem: You can't preview it without .wwz!
  # Maybe have local redirects VERSION/test/wild/ to 
  #
  # Instead of linking, I should compress them all here.

  copy-web

  tree $root
}

deploy-doc() {
  local deploy_repo='../oilshell.org__deploy'
  local release_root_dir="$deploy_repo/release"
  local release_dir="$release_root_dir/$OIL_VERSION"

  cp -v -r --force --no-target-directory \
    _release/VERSION/ $release_dir/

  # Generate release index.
  html-index $release_root_dir _tmp/releases.html
  cp -v _tmp/releases.html $deploy_repo

  tree -L 3 $release_root_dir
  
  ls -l $deploy_repo/releases.html
}

readonly DOWNLOAD_DIR='../oilshell.org__deploy/download/'

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

pretty-size() {
  local path=$1
  stat --format '%s' "$path" | python -c '
import sys
num_bytes = int(sys.stdin.read())
print "{:,}".format(num_bytes)
'
}

# NOTE: It might be better to link to files like this in the /release/ tree.
# Although I am not signing them.

# https://nodejs.org/dist/v8.11.4/SHASUMS256.txt.asc

_tarball-links-row-html() {
  local version=$1

  cat <<EOF
<tr class="file-table-heading">
  <td></td>
  <td>File / SHA256 checksum</td>
  <td class="size">Size</td>
  <td></td>
</tr>
EOF

  # only release .xz for oils-for-unix
  for name in oil-$version.tar.{xz,gz} oils-for-unix-$version.tar.xz; do
    local url="/download/$name"  # The server URL
    local path="../oilshell.org__deploy/download/$name"

    # The native version might not exist
    if [[ $name == oils-for-unix-* && ! -f $path ]]; then
      continue
    fi

    local checksum
    checksum=$(sha256sum $path | awk '{print $1}')
    local size
    size=$(pretty-size $path)

    # TODO: Port this to oil with "commas" extension.

    # Three columns: date, version, and links
    cat <<EOF
    <tr> 
      <td></td>
      <td class="filename"><a href="$url">$name</a></td>
      <td class="size">$size</td>
    </tr>
    <tr>
      <td></td>
      <td colspan=2 class="checksum">$checksum</td>
    </tr>
EOF
  done
}

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
    version=$(head -n 1 $dir/oil-version.txt)
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

    _tarball-links-row-html $version

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
    <title>Oil Releases</title>
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
      <a href="/">oilshell.org</a>
    </p>
    <h1>Oil Releases</h1>

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

dep-wild-testdata() {
  test/wild.sh fetch-archive
  test/wild.sh extract-archive
  test/wild.sh manifest-from-archive
}

dep-benchmarks() {
  benchmarks/osh-runtime.sh download
  benchmarks/osh-runtime.sh extract

  benchmarks/ovm-build.sh download
  benchmarks/ovm-build.sh extract-other

  # For ovm-build benchmark.
  build/codegen.sh download-clang
  build/codegen.sh extract-clang
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

    # test/wild.sh
    dep-wild-testdata

    dep-benchmarks
  fi
}

# This is a hack because the Makefile dependencies aren't correct.
quick-oil-tarball() {
  # Can't delete _gen/_devbuild because there are source files there we want
  rm -r -f --verbose _bin _build _release

  make _bin/oil.ovm-dbg

  local in=_release/oil.tar
  local out=_release/oil-$OIL_VERSION.tar.gz

  make $in
  time gzip -c $in > $out
  ls -l $out
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
