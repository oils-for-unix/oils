#!/usr/bin/env bash
#
# Usage:
#   build/dev-guide.sh build-dev-guide
#
# This will clone the oils-for-unix/oils wiki, and build all of the markdown
# files using doc tools. The docs are saved to _release/VERSION/doc/wiki.
#
# This can be used for the dev guide which is located at
# _release/VERSION/doc/wiki/Dev-Guide.html.

set -e

readonly HTML_BASE_DIR=_release/VERSION
readonly WIKI_DIR=_tmp/wiki

has-wiki() {
  test -d "$WIKI_DIR"
}

clone-wiki() {
  if has-wiki; then
    echo "Wiki already cloned to $WIKI_DIR, pulling latest"

    pushd "$WIKI_DIR"
    git pull
    popd
    return
  fi

  echo "Cloning wiki to $WIKI_DIR"
  mkdir -p "$WIKI_DIR"
  git clone https://github.com/oils-for-unix/oils.wiki.git "$WIKI_DIR"
}

pre-render-wikilinks() {
  ## GitHub wikis have a unique [[link syntax]] which references topic within
  ## the wiki.
  ##
  ## This function converts that syntax to the traditional
  ## [link syntax](./link-syntax.html) which will render correctly once fed to
  ## doctools.
  local script=$(cat <<'EOF'
import sys
import re

def slugify(text: str) -> str:
    """
    The links are given in "human-form" but we need to turn then into links or
    "slugs" which correspond to the rendered file name.

    Note: Some titles have commas in them. These are not present in the slug.
    """
    return text.replace(" ", "-").replace(",", "")

link_pattern = re.compile(r"\[\[(.*?)\]\]")

def replacer(match):
    text = match.group(1).strip()
    return f"[{text}](./{slugify(text)}.html)"

input_text = sys.stdin.read()
output_text = link_pattern.sub(replacer, input_text)
sys.stdout.write(output_text)
EOF
)

  python3 -c "$script"
}

build-one() {
  local path=$1
  local name=$(basename "$path")
  local name=${name%.md}  # Remove .md extension
  local name=${name/,//}  # Remove commas in names (breaks doctools)
  local title=$(echo "$name" | sed 's/ /-/g')

  mkdir -p "$HTML_BASE_DIR/doc/wiki/"

  local web_url="../../web"
  build/doc.sh render-only \
    <(pre-render-wikilinks <"$path") \
    "$HTML_BASE_DIR/doc/wiki/$name.html" \
    "$web_url/base.css $web_url/manual.css $web_url/toc.css $web_url/language.css $web_url/code.css" \
    "$title"
}

build-dev-guide() {
  clone-wiki
  find "$WIKI_DIR" -name '*.md' -print0 | xargs -I {} -0 -- $0 build-one {}
}

"$@"
