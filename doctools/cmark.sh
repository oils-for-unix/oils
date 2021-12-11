#!/usr/bin/env bash
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

REPO_ROOT=$(cd $(dirname $0)/.. && pwd)
readonly REPO_ROOT

readonly TAR_DIR=$REPO_ROOT/_cache
readonly DEPS_DIR=$REPO_ROOT/../oil_DEPS

readonly CMARK_VERSION=0.29.0
readonly URL="https://github.com/commonmark/cmark/archive/$CMARK_VERSION.tar.gz"

# 5/2020: non-hermetic dependency broke with Python 3 SyntaxError!  Gah!  TODO:
# make this hermetic.
#
# https://pypi.org/project/Pygments/#history
#
# Installing through pip doesn't work.  Tarballs are better...  TODO: Put this
# in 'toil'.

# https://github.com/robotframework/RIDE/issues/2161
install-pygments() {
  #sudo -H pip install -U --force 'pygments==2.5.1'

  # Why the heck does this install pygments 2.6.1 ?
  # pip install 'pygments==2.5.1'

  echo TODO
}

download() {
  mkdir -p $TAR_DIR
  wget --no-clobber --directory $TAR_DIR $URL
}

extract() {
  pushd $TAR_DIR
  tar -x -z < $(basename $URL)
  popd
}

build() {
  mkdir -p $DEPS_DIR/cmark
  pushd $DEPS_DIR/cmark

  # Configure
  cmake $TAR_DIR/cmark-0.29.0/

  # Compile
  make

  # This tests with Python 3, but we're using cmark via Python 2.
  # It crashes on some systems due to the renaming of cgi.escape -> html.escape
  # (issue 792)
  # The 'demo-ours' test is good enough for us.
  #make test

  popd

  # Binaries are in build/src
}

make-symlink() {
  #sudo make install
  ln -s -f -v $DEPS_DIR/cmark/src/libcmark.so $DEPS_DIR/
  ls -l $DEPS_DIR/libcmark.so
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
