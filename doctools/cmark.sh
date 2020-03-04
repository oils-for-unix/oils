#!/bin/bash
#
# Usage:
#   doctools/cmark.sh <function name>
#
# Example:
#   doctools/cmark.sh download
#   doctools/cmark.sh extract
#   doctools/cmark.sh build
#   doctools/cmark.sh run-tests (also installs it)
#   doctools/cmark.sh demo-ours  # smoke test

set -o nounset
set -o pipefail
set -o errexit

readonly URL='https://github.com/commonmark/cmark/archive/0.29.0.tar.gz'

download() {
  mkdir -p _deps
  wget --no-clobber --directory _deps $URL
}

readonly CMARK_DIR=_deps/cmark-0.29.0

extract() {
  pushd _deps
  tar -x -z < $(basename $URL)
  popd
}

build() {
  pushd $CMARK_DIR
  # GNU make calls cmake?
  make
  popd

  # Binaries are in build/src
}

run-tests() {
  pushd $CMARK_DIR
  make test
  sudo make install
  popd
}

demo-theirs() {
  echo '*hi*' | cmark
}

demo-ours() {
  export PYTHONPATH=.

  echo '*hi*' | doctools/cmark.py

  # This translates to <code class="language-sh"> which is cool.
  #
  # We could do syntax highlighting in JavaScript, or simply post-process HTML

  doctools/cmark.py <<'EOF'
```sh
code
block
```

```oil
code
block
```
EOF

  # The $ syntax can be a little language.
  #
  # $oil-issue
  # $cross-ref
  # $blog-tag
  # $oil-source-file
  # $oil-commit

  doctools/cmark.py <<'EOF'
[click here]($xref:re2c)
EOF

  # Hm for some reason it gets rid of the blank lines in HTML.  When rendering
  # to text, we would have to indent and insert blank lines?  I guess we can
  # parse <p> and wrap it.

  doctools/cmark.py <<'EOF'
Test spacing out:

    echo one
    echo two

Another paragraph with `code`.
EOF

}

"$@"
