#!/usr/bin/env bash
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# http://oilshell.org/$VERSION/
#  doc/
#    INSTALL.txt -- for people who want to try it
#    osh-quick-ref.html -- A single page
#    osh-manual.html    -- more stuff

# Do we want:
# - spec/unit/gold/wild test results?
# - benchmarks?

# maybe:
# $VERSION/
#   doc/
#   test/
#   benchmarks/
#
# Just like the repo layout.

# Another idea:
#
# http://oilshell.org/release/
#   $VERSION/
#     oil-0.0.0.tar.gz   # This should probably go on a different host
#     doc/
#     test/
#     benchmarks/

readonly OIL_VERSION=$(head -n 1 oil-version.txt)
export OIL_VERSION  # for quick_ref.py

log() {
  echo "$@" 1>&2
}

#
# Deps (similar to devtools/cmark.sh and build/codegen.sh)
#

readonly MANDOC_DIR='_deps/mdocml-1.14.1'

download-mandoc() {
  mkdir -p _deps
  wget --no-clobber --directory _deps \
    https://mandoc.bsd.lv/snapshots/mdocml-1.14.1.tar.gz
}

build-mandoc() {
  cd $MANDOC_DIR
  ./configure
  make
}

mandoc() {
  $MANDOC_DIR/mandoc "$@"
}

_build-timestamp() {
  echo '<hr/>'
  echo "<i>Generated on $(date)</i>"
}

# Places version is used
#
# - in --version
# - in URL for every page?  inside the binary
# - in titles for index, install, osh-quick-ref TOC, etc.
# - in deployment script

# Run with environment variable
_quick-ref() {
  build/quick_ref.py "$@"
}

x-quick-ref() {
  local prog=$1
  local out_dir=$2

  local html_out=$out_dir/doc/$prog-quick-ref.html
  local text_out_dir=_devbuild/$prog-quick-ref
  local py_out=_devbuild/gen/${prog}_help.py

  mkdir -p $out_dir/doc $text_out_dir

  {
    cat <<EOF
<!DOCTYPE html>
<html>
  <head>
    <style>
      a:link {
        text-decoration: none;
      }
      a:hover {
        text-decoration: underline;
      }
      body {
        margin: 0 auto;
        width: 40em;
      }
      /* different color because they're links but not topics */
      .level1 {
        /* color: green; */
        color: black;
      }
      .level2 {
        color: #555;
      }
      h1,h2,h3,h4 {
      /* color: darkcyan; */
      }
      #home-link {
        text-align: right;
      }
    </style>
  </head>
  <body>
    <p id="home-link">
      <a href="/">oilshell.org</a>
    </p>
    <p style="color: darkred; font-size: x-large;">
      NOTE: This document is a work in progress!
    </p>
EOF

    _quick-ref toc doc/${prog}-quick-ref-toc.txt

    # Also generate the _devbuild/osh-quick-ref/ dir
    _quick-ref pages doc/${prog}-quick-ref-pages.txt $text_out_dir $py_out

    _build-timestamp
    cat <<EOF
  </body>
</html>
EOF
  } > $html_out
  log "Wrote $html_out"
}

osh-quick-ref() {
  local out_dir=${1:-_release/VERSION}
  x-quick-ref osh $out_dir
}

markdown2html() {
  local src=$1
  local out=$2
  local more_css_link=${3:-}

  { cat <<EOF
<!DOCTYPE html>
<html>
  <head>
    $more_css_link
  </head>
  <body>
    <p id="home-link">
      <a href="/releases.html">all releases</a> |
      <a href="/">oilshell.org</a>
    </p>
EOF
  
    devtools/cmark.py < $src

    _build-timestamp
    cat <<EOF
  </body>
</html>
EOF
  } > $out
}

release-index() {
  local out=${1:-_tmp/release-index.html}
  # NOTE: We're at /release/0.6.pre10/index.html, and then there is a
  # web/release-index.css file in each release tree.

  # Not monospace
  local css_link='<link rel="stylesheet" type="text/css" href="web/release-index.css" />'
  markdown2html doc/release-index.md $out "$css_link" ''
}

install() {
  local root_dir=${1:-_release/VERSION}
  local css_link='<link rel="stylesheet" type="text/css" href="../web/install.css" />'
  markdown2html INSTALL.txt $root_dir/doc/INSTALL.html "$css_link"
}

manual() {
  local root_dir=${1:-_release/VERSION}
  local release_date=${2:-}

  local css_link='
    <link rel="stylesheet" type="text/css" href="../web/manual.css" />
    <link rel="stylesheet" type="text/css" href="../web/toc.css" />
  '

  # TODO: cmark.py could replace <span class="date"></span> with -v date=?
  for d in osh-manual known-differences; do
    markdown2html doc/$d.md $root_dir/doc/$d.html "$css_link" ''
  done
  ls -l $root_dir/doc
}

# TODO: This could use some CSS.
man-page() {
  local root_dir=${1:-_release/VERSION}
  mandoc -T html doc/osh.1 > $root_dir/osh.1.html
  ls -l $root_dir
}

# I want to ship the INSTALL file literally, so just mutate things
_sed-ext() {
  sed --regexp-extended -i "$@"
}

update-src-versions() {
  _sed-ext \
    "s/[0-9]+\.[0-9]+\.[a-z0-9]+/$OIL_VERSION/g" \
    doc/release-index.md doc/osh-manual.md

  _sed-ext \
    "s/oil-[0-9]+\.[0-9]+\.[a-z0-9]+/oil-$OIL_VERSION/g" INSTALL.txt

  _sed-ext \
    "s;/release/[0-9]+\.[0-9]+\.[a-z0-9]+/;/release/$OIL_VERSION/;g" \
    INSTALL.txt doc/osh-quick-ref-toc.txt doc/osh.1
}

oil-grammar() {
  PYTHONPATH=. oil_lang/cmd_parse.py "$@"
}

"$@"
