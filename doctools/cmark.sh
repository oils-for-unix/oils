#!/bin/bash
#
# Usage:
#   doctools/cmark.sh <function name>
#
# Example:
#   doctools/cmark.sh download
#   doctools/cmark.sh extract
#   doctools/cmark.sh build
#   doctools/cmark.sh make-symlink
#   doctools/cmark.sh demo-ours  # smoke test

set -o nounset
set -o pipefail
set -o errexit

readonly CMARK_VERSION=0.29.0
readonly URL="https://github.com/commonmark/cmark/archive/$CMARK_VERSION.tar.gz"

download() {
  mkdir -p _deps
  wget --no-clobber --directory _deps $URL
}

readonly CMARK_DIR=_deps/cmark-$CMARK_VERSION

extract() {
  pushd _deps
  tar -x -z < $(basename $URL)
  popd
}

build() {
  pushd $CMARK_DIR
  # GNU make calls cmake?
  make
  make test
  popd

  # Binaries are in build/src
}

make-symlink() {
  #sudo make install
  ln -s -f -v cmark-$CMARK_VERSION/build/src/libcmark.so _deps/
  ls -l _deps/libcmark.so
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
