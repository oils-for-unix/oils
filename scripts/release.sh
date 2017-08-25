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

# TODO: enforce that there is a release-0.0.0 branch?
build-and-test() {
  rm -r -f _devbuild _build _release
  rm -f _bin/oil.*

  build/pylibc.sh build  # for libc.so
  build/doc.sh osh-quick-ref  # for _devbuild/osh_help.py

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

  # TODO: Make a clean alpine chroot?
  test/alpine.sh copy-tar oil
  test/alpine.sh test-tar oil
}

# Release procedure after build-and-test:
#
# ./local.sh publish-doc
# ./local.sh publish-release
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

publish-doc() {
  local user=$1
  local host=$2

  build/doc.sh osh-quick-ref
  build/doc.sh install
  build/doc.sh index
  rsync --archive --verbose \
    _build/doc/ "$user@$host:oilshell.org/release/$OIL_VERSION/doc/"

  echo "Visit https://www.oilshell.org/release/$OIL_VERSION/doc/"
}

publish-release() {
  local user=$1
  local host=$2

  rsync --archive --verbose \
    _release/oil-$OIL_VERSION.tar.* \
    "$user@$host:oilshell.org/download/"

  echo "Visit https://www.oilshell.org/download/"
}

publish-release-html() {
  local user=$1
  local host=$2

  rsync --archive --verbose \
    _tmp/releases.html \
    "$user@$host:oilshell.org/"
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
    local url="/download/$name"  # The server URL
    local path=_download/$name
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

_html-index() {
  local in_dir=${1:-_download}  # the download directory we want to make an index of

  local tmp_dir=_tmp/release-html
  mkdir -p $tmp_dir

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

  for tar in $in_dir/*.gz; do  # all releases
    log "--- $tar"
    local version=$(basename $tar .gz | egrep --only-matching '[0-9]+\.[0-9]+\.[a-z0-9]+')
    log "Version: $version"

    local bytecode_rel_path=oil-$version/_build/oil/bytecode.zip
    tar --extract --gzip --file $tar --directory $tmp_dir $bytecode_rel_path
    local bytecode_path=$tmp_dir/$bytecode_rel_path
    local release_date=$(unzip -p $bytecode_path release-date.txt)
    log "Release date: $release_date"
    log ""

    local announce_url
    case $version in
      0.0.0)
        announce_url='/blog/2017/07/23.html'
        ;;
      *)
        # TODO: Fail?
        announce_url="javascript:alert('No release announcement');"
    esac

    # anchor
    echo '<a name="'$version'"></a>'
    echo "<h2>Version $version</h2>"

    echo "<p>Release Date: $release_date</p>"

    echo '<p>                 <a href="'"$announce_url"'">Release Announcment</a>
              &nbsp; | &nbsp; <a href="/release/'$version'/doc/INSTALL.html">INSTALL</a>
              &nbsp; | &nbsp; <a href="/release/'$version'/doc/">Docs</a>
          </p>'
              #&nbsp; | &nbsp; <a href="/release/'$version'/test/">Test Results</a>

    _release-files-html $version

    #unzip -p $bytecode_path oil-version.txt
  done

  #tree _tmp/html
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
        color: #888;
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
  local out=_tmp/releases.html
  { _html-header
    _html-index "$@" 
    _html-footer
  } > $out
  ls -l $out
}

"$@"
