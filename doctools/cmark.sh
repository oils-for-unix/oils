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
# 7/2023: Download the wheel file
# doctools/oil_doc.py OPTIONALLY uses this
#
# It's only used in the blog, so let's just put it in the oilshell.org repo,
# not the oil repo

download-old-pygments() {
  wget --directory _tmp --no-clobber \
    'https://files.pythonhosted.org/packages/be/39/32da3184734730c0e4d3fa3b2b5872104668ad6dc1b5a73d8e477e5fe967/Pygments-2.5.2-py2.py3-none-any.whl'
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
