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
# doctools/oils_doc.py OPTIONALLY uses this
#
# It's only used in the blog, so let's just put it in the oilshell.org repo,
# not the oil repo
#
# 12/2024: I want a Markdown highlighter for doc/ul-table.md.  It will look
# nicer.

download-old-pygments() {
  wget --directory _tmp --no-clobber \
    'https://files.pythonhosted.org/packages/be/39/32da3184734730c0e4d3fa3b2b5872104668ad6dc1b5a73d8e477e5fe967/Pygments-2.5.2-py2.py3-none-any.whl'
}

demo-theirs() {
  echo '*hi*' | cmark
}

cmark-py() {
  PYTHONPATH='.:vendor' doctools/cmark.py "$@"
}

demo-ours() {
  export PYTHONPATH=.

  echo '*hi*' | cmark-py

  # This translates to <code class="language-sh"> which is cool.
  #
  # We could do syntax highlighting in JavaScript, or simply post-process HTML

  cmark-py <<'EOF'
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

  cmark-py <<'EOF'
[click here]($xref:re2c)
EOF

  # Hm for some reason it gets rid of the blank lines in HTML.  When rendering
  # to text, we would have to indent and insert blank lines?  I guess we can
  # parse <p> and wrap it.

  cmark-py <<'EOF'
Test spacing out:

    echo one
    echo two

Another paragraph with `code`.
EOF
}

demo-quirks() {
  ### Cases that came from writing ul-table

  export PYTHONPATH=.

  cmark-py --common-mark <<'EOF'
1. what `<table>`
EOF

  # Very annoying: list items can't be empty
  # <span />
  cmark-py --common-mark <<'EOF'
<table>

- thead
  - <!-- list item can't be empty -->
  - Proc
  - Func

</table>
EOF

  cmark-py --common-mark <<'EOF'
- <tr-attrs class=foo /> text required here
  - one
  - two
EOF

cmark-py --common-mark <<'EOF'
- tr <tr-attrs class=foo />
  - one
  - two
EOF

  # Weird case - the `proc` is sometimes not expanded to <code>proc</code>
  cmark-py --common-mark <<'EOF'
- <span /> ... More `proc` features
- <span />
  More `proc` features 
- <span /> <!-- why does this fix it? -->
  More `proc` features 
EOF

  # This has &amp; in an attr value, which our HTML lexer needs to handle
  cmark-py --common-mark <<'EOF'
from [ampersand][]

[ampersand]: http://google.com/?q=foo&z=z
EOF

  # Only &nbsp; is standard
  cmark-py --common-mark <<'EOF'
- tr
  - &nbsp; -
  - &sp; -
  - &zwsp; -
EOF

  # BUG: parse error because backticks span a line

  return
  cmark-py <<'EOF'
1. The Markdown translator produces a `<table> <ul> <li> ... </li> </ul>
   </table>` structure.
EOF
}

demo-htm8() {
  ### Cases that came from developing HTM8

  export PYTHONPATH=.

  cmark-py --common-mark <<'EOF'
[bash]($xref:bash)

[other][]

[other]: $xref

EOF
}

demo-quarto() {
  ### Cases that came from developing HTM8

  export PYTHONPATH=.

  # Standard Markdown
  cmark-py --common-mark <<'EOF'

Hello

    code
    block

Python:

```python
print("hi")
```
EOF

  # Quarto extensions
  # Turns out as class="language-{python} which isn't ideal
  cmark-py --common-mark <<'EOF'

Executable Python

```{python}
print("hi")
```

With attributes

```{python}
#| attr: value
#| fig-cap: "A line plot"
print("hi")
```
EOF

  # Another syntax I saw
  # This appears to be  R Markdown, which is an older syntax that Quarto
  # doesn't use
  # But it accepts
  #
  # Hm cmark omits everything after the space

  cmark-py --common-mark <<'EOF'

Executable Python

```{r setup, include=FALSE}
print("hi")
```
EOF
}

"$@"
