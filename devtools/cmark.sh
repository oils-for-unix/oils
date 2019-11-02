#!/bin/bash
#
# Usage:
#   ./cmark.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

download() {
  mkdir -p _deps
  wget --no-clobber --directory _deps \
    https://github.com/commonmark/cmark/archive/0.28.3.tar.gz
}

readonly CMARK_DIR=_deps/cmark-0.28.3

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
  echo '*hi*' | devtools/cmark.py

  # This translates to <code class="language-sh"> which is cool.
  #
  # We could do syntax highlighting in JavaScript, or simply post-process HTML

  devtools/cmark.py <<'EOF'
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

  devtools/cmark.py <<'EOF'
[click here]($cross-ref:re2c)
EOF

}


"$@"
