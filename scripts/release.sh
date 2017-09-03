#!/bin/bash
#
# Usage:
#   ./release.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly OIL_VERSION=$(head -n 1 oil-version.txt)

log() {
  echo "$@" 1>&2
}

# TODO:
# - enforce that there is a release/$VERSION branch?

# oilshell.org__deploy/
#   releases.html
#   opy-releases.html  (later)
#   release/
#     $VERSION/
#       index.html  # links to all this stuff
#       oil-version.txt
#       release-date.txt
#       Changelog.txt  # raw git log, release announcement is prose
#       doc/
#         INSTALL.html
#         osh-quick-ref.html
#       test/  # results
#         spec/
#         unit/
#         wild/
#         gold/
#         tarball/  # log of building and running the tarball?
#       metrics/  # static metrics on source code?
#                 # could also do cloc?
#         loc-src.txt  # oil, tools, etc.
#         loc-pydeps.txt  (build/stats.sh line counts)
#         loc-nativedeps.txt
#         number of functions, classes, etc.?
#         bytecode/bundle size, binary size on x86_64
#         tarball size?
#       coverage/  # coverage of all spec tests?  And gold tests maybe?
#         python/  # python stdlib coverage  with pycoverage
#         c/       # c coverage with gcc/clang
#       benchmarks/
#         machine-lisa/
#           proc/meminfo etc.
#           compile time on my machine (serial, optimized, etc.)
#           startup time for hello world
#           osh speed test, opy compiling, etc.
#         machine-pizero/
#   download/
#     0.0.0/  # TODO: Add version here, so we can have binaries too?
#       oil-0.0.0.tar.xz 

# NOTE: Also need build/doc.sh update-src-versions to change doc/index.md, etc.

build-and-test() {
  rm -r -f _devbuild _build _release
  rm -f _bin/oil.*

  build/dev.sh pylibc  # for libc.so, needed to crawl deps
  build/doc.sh osh-quick-ref  # for _devbuild/osh_help.py

  # TODO: publish these
  test/unit.sh all

  build/prepare.sh configure
  build/prepare.sh build-python

  # Could do build/prepare.sh test too?
  make clean
  make

  # Make sure
  test/spec.sh smoke

  test/spec.sh all

  # Build the oil tar
  $0 oil

  # Test the oil tar
  build/test.sh oil-tar

  # NOTE: Need test/alpine.sh download;extract;setup-dns,add-oil-build-deps, etc.

  test/alpine.sh copy-tar oil
  test/alpine.sh test-tar oil
}

# Release procedure after build-and-test:
#
# ./local.sh publish-doc
# ./local.sh publish-release
# ./local.sh publish-releases-html
# ./local.sh publish-spec

# TODO:
# - publish-unit
# - Update the doc/ "latest" redirect?
# - Publish Alpine test log?  (along with build stats?)

_compressed-tarball() {
  local name=${1:-hello}
  local version=${2:-0.0.0}

  local in=_release/$name.tar
  local out=_release/$name-$version.tar.gz

  # Overwrite it to cause rebuild of oil.tar (_build/oil/bytecode.zip will be
  # out of date.)
  build/actions.sh write-release-date

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

deploy-doc() {
  local deploy_repo='../oilshell.org__deploy'
  local release_root_dir="$deploy_repo/release"
  local release_dir="$release_root_dir/$OIL_VERSION"

  mkdir -p $release_dir/{doc,test,metrics}

  # Metadata
  cp -v _build/release-date.txt oil-version.txt $release_dir

  # Line counts.  TODO: It would be nicer to make this structured data somehow.
  scripts/count.sh all \
    > $release_dir/metrics/linecount-src.txt  # Count repo lines
  build/metrics.sh linecount-pydeps \
    > $release_dir/metrics/linecount-pydeps.txt
  build/metrics.sh linecount-nativedeps \
    > $release_dir/metrics/linecount-nativedeps.txt

  # Tests
  cp -v -r --no-target-directory _tmp/spec/ $release_dir/test/spec

  # Generate release index.
  html-index $release_root_dir _tmp/releases.html
  cp -v _tmp/releases.html $deploy_repo

  build/doc.sh osh-quick-ref
  # Generate docs.
  build/doc.sh install
  build/doc.sh index

  cp -v -r --no-target-directory _build/doc/ $release_dir/doc

  tree -L 3 $release_root_dir
  
  ls -l $deploy_repo/releases.html
}

# I think these aren't checked into git?  They can just be managed separately?
# Or should you check in the sha checksums?  Those will be in releases.html,
# but a CSV might be nice.
deploy-tar() {
  local download_dir='../oilshell.org__deploy/download/'
  mkdir -p $download_dir

  cp -v _release/oil-$OIL_VERSION.tar.* $download_dir

  ls -l $download_dir
}

#
# Generate release.html.
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

_release-files-html() {
  local version=$1

  echo '<table class="file-table">'
  echo '<tr><thead> <td>File</td> <td>Size</td> <td>SHA256 Checksum</td> </thead></tr>'

  for name in oil-$version.tar.{xz,gz}; do
    local url="download/$name"  # The server URL
    local path=../oilshell.org__deploy/download/$name
    local checksum=$(sha256sum $path | awk '{print $1}')
    local size=$(stat --format '%s' $path)

    # TODO: Port this to oil with "commas" extension.

    echo '<tr> <td class="filename"><a href="'$url'">'$name'</a></td>
               <td class="size">'$size'</td>
               <td class="checksum">'$checksum'</td>
         </tr>'
  done
  echo '</table>'
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

    local version=$(head -n 1 $dir/oil-version.txt)
    local release_date=$(head -n 1 $dir/release-date.txt)

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

    local announce_url
    case $version in
      0.0.0)
        announce_url='blog/2017/07/23.html'
        ;;
      *)
        # TODO: Fail?
        announce_url="javascript:alert('No release announcement');"
    esac

    # anchor
    echo '<a name="'$version'"></a>'
    echo "<h2>Version $version</h2>"

    echo "<p class="date">$date</p>"

    echo '<p>                 <a href="'"$announce_url"'">Release Announcment</a>
              &nbsp; | &nbsp; <a href="release/'$version'/doc/INSTALL.html">INSTALL</a>
              &nbsp; | &nbsp; <a href="release/'$version'/">Docs and Details</a>
          </p>'
              #&nbsp; | &nbsp; <a href="/release/'$version'/test/">Test Results</a>

    _release-files-html $version
  done < _tmp/sorted-releases.txt
}

_html-header() {
  cat <<EOF
<html>
  <head>
    <title>Oil Releases</title>
    <style>
      /* Make it centered and skinny for readability */
      body {
        margin: 0 auto;
        width: 60em;
      }
      h1 {
        text-align: center;
      }
      thead {
        font-weight: bold;
      }
      /* Style for checksum, file size, etc. */

      .file-table {
        width: 100%;
      }

      .filename {
        font-family: monospace;
      }

      .size {
      }
      .checksum {
        font-family: monospace;
        color: #555;
      }

      /* Copied from oilshell.org bundle.css */
      .date {
        font-size: medium;
        color: #555;
        padding-left: 1em;
      }
    </style>
  </head>
  <body>
    <p></p>
    <h1>Oil Releases</h1>
EOF
}

_html-footer() {
  cat <<EOF
  </body>
</html>
EOF
}

html-index() {
  local release_root_dir=$1
  local out=${2:-_tmp/releases.html}

  { _html-header
    _html-index $release_root_dir
    _html-footer
  } > $out
  ls -l $out
}

"$@"
