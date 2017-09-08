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

  local html_out=_build/doc/$prog-quick-ref.html
  local text_out_dir=_build/$prog-quick-ref
  local py_out=_devbuild/${prog}_help.py

  mkdir -p _build/doc $text_out_dir _devbuild
  touch _devbuild/__init__.py  # so osh_help is importable

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
        width: 50em;
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
    </style>
  </head>
  <body>
    <p style="color: darkred; font-size: x-large;">
      NOTE: This document is a work in progress!
    </p>
EOF

    _quick-ref toc doc/${prog}-quick-ref-toc.txt

    # Also generate _build/osh-quick-ref/ dir
    _quick-ref pages doc/${prog}-quick-ref-pages.txt $text_out_dir $py_out

    _build-timestamp
    cat <<EOF
  </body>
</html>
EOF
  } > $html_out
}

osh-quick-ref() {
  x-quick-ref osh "$@"
}

oil-quick-ref() {
  x-quick-ref oil "$@"
}

markdown2html() {
  local src=$1
  local out=$2
  local monospace=${3:-}
  mkdir -p _build/doc

  { cat <<EOF
<!DOCTYPE html>
<html>
  <head>
    <style>
      body {
        margin: 0 auto;
        width: 40em;
        $monospace
      }
      pre {
        color: green;
        margin-left: 4em;
      }
    </style>
  </head>
  <body>
EOF
  
    markdown < $src  # TODO: CommonMark

    _build-timestamp
    cat <<EOF
  </body>
</html>
EOF
  } > $out
}

readonly MONOSPACE='font-family: monospace;'

install() {
  markdown2html INSTALL.txt _build/doc/INSTALL.html "$MONOSPACE"
}

release-index() {
  local out=${1:-_build/doc/release-index.html}
  # Not monospace
  markdown2html doc/release-index.md $out ''
}

# I want to ship the INSTALL file literally, so just mutate things
_sed-ext() {
  sed --regexp-extended -i "$@"
}

update-src-versions() {
  _sed-ext \
    "s/Version [0-9]+.[0-9]+.[a-z0-9]+/Version $OIL_VERSION/g" \
    doc/release-index.md

  _sed-ext \
    "s/oil-[0-9]+.[0-9]+.[a-z0-9]+/oil-$OIL_VERSION/g" INSTALL.txt
}

"$@"
