#!/bin/bash
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

publish() {
  echo 'Hello from run.sh'
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

osh-quick-ref() {
  local html_out=_tmp/doc/osh-quick-ref.html
  local text_dir=_build/osh-quick-ref

  local py_out=_build/osh_help.py

  mkdir -p _tmp/doc $text_dir
  touch _build/__init__.py  # so osh_help is importable

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
    </style>
  </head>
  <body>
    <p style="color: darkred; font-size: x-large;">
      NOTE: This document is a work in progress!
    </p>
EOF

    # TODO: Add version and URL
    doc/quick_ref.py toc doc/osh-quick-ref-toc.txt

    # Also generate _build/osh-quick-ref/ dir
    doc/quick_ref.py pages \
      doc/osh-quick-ref-pages.txt $text_dir $py_out

    _build-timestamp
    cat <<EOF
  </body>
</html>
EOF
  } > $html_out

  echo "Wrote $html_out"
}

markdown2html() {
  local src=$1
  local out=$2
  local monospace=${3:-}
  mkdir -p _tmp/doc

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
  markdown2html INSTALL _tmp/doc/INSTALL.html "$MONOSPACE"
}

index() {
  # Not monospace
  markdown2html doc/index.md _tmp/doc/index.html ''
}

# TODO: TOC is one doc?  Maybe use Makefile.

# Output:
#
# _build/doc/
#   osh-quick-ref-pages.html
#   osh-quick-ref-toc.html
#   osh-quick-ref.html  # concatenated with sed or something?
#
# _build/doc/osh-quick-ref/
#   1.txt
#   1-1.txt
#   1-1-1.txt
#   1-1-2.txt
#   1.2
#   2
#   2.1
#
# and then osh/help_topics.py
#
# HELP_TOPICS = { 'true': "1.1.1", "false": "1.1.1" }
#
# LATER: Fuzzy matching of help topics

"$@"
