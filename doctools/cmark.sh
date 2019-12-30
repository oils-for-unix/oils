#!/bin/bash
#
# Usage:
#   ./cmark.sh <function name>

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

travis-hack() {
  ### Check the libcmark.so into git.  This only works on Ubuntu!
  # We're doing this because otherwise we'll have to download the tarball on
  # every Travis build, install cmake, build it, and install it.  That's not
  # terrible but it slows things down a bit.

  local so=$(echo $CMARK_DIR/build/src/libcmark.so.*)
  ls -l $so
  echo
  ldd $so

  cp -v $so doctools/travis-bin
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
