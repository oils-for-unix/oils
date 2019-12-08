#!/usr/bin/env bash
#
# Usage:
#   build/doc.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# https://oilshell.org/release/$VERSION/
#  doc/
#    index.html
#    INSTALL.html

readonly OIL_VERSION=$(head -n 1 oil-version.txt)
export OIL_VERSION  # for quick_ref.py

log() {
  echo "$@" 1>&2
}

#
# Deps (similar to devtools/cmark.sh and build/codegen.sh)
#

readonly MANDOC_DIR='_deps/mdocml-1.14.1'

download-mandoc() {
  mkdir -p _deps
  wget --no-clobber --directory _deps \
    https://mandoc.bsd.lv/snapshots/mdocml-1.14.1.tar.gz
}

build-mandoc() {
  cd $MANDOC_DIR
  ./configure
  make
}

mandoc() {
  $MANDOC_DIR/mandoc "$@"
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

# Run with environment variable
_make-help() {
  devtools/make_help.py "$@"
}

cmark() {
  # h2 and h3 are shown in TOC.  The blog uses "legacy" h3 and h4.
  devtools/cmark.py --toc-tag h2 --toc-tag h3 --toc-pretty-href "$@"
}

readonly MARKDOWN_DOCS=(
  # Help index has its own rendering

  # polished
  osh-manual known-differences
  errors
  errexit
  json

  # needs polish
  # Note: docs about the Oil language are prefixed 'oil-'.
  # data-model and command-vs-expression-mode span both OSH and Oil.

  index
  what-is-oil
  oil-overview
  oil-options
  oil-keywords
  oil-builtins
  command-vs-expression-mode
  oil-expressions
  oil-word-language
  oil-special-vars
  oil-proc-func-block
  eggex
  unicode

  data-model
  architecture-notes
)

readonly TIMESTAMP=$(date)

split-and-render() {
  local src=${1:-doc/known-differences.md}

  local name=$(basename $src .md)
  local out=${2:-_release/VERSION/doc/$name.html}

  local prefix=_tmp/doc/$name

  # Also add could add css_files.  The one in the file takes precedence always?

  # css_files: a space-separated list
  # all_docs_url: so we link from doc/foo.html -> doc/

  devtools/split_doc.py \
    -v build_timestamp="$TIMESTAMP" \
    -v oil_version="$OIL_VERSION" \
    -v css_files='../web/manual.css ../web/toc.css' \
    -v all_docs_url='.' \
    -v repo_url="$src" \
    $src $prefix

  #ls -l _tmp/doc
  #head _tmp/doc/*
  #return

  cmark ${prefix}_meta.json ${prefix}_content.md > $out
  log "Wrote $out"
}

# Special case for README
# Do NOT split because we don't want front matter in the markdown source.
render-only() {
  local src=${1:-README.md}
  local css_files=${2:-'../web/manual.css ../web/toc.css'}
  local title=${3:-'Oil Source Code'}

  local name
  case $src in 
    *.md)
      name=$(basename $src .md)
      ;;
    *.txt)
      name=$(basename $src .txt)
      ;;
    *)
      name=$(basename $src)
      ;;
  esac

  local prefix=_tmp/doc/$name
  local out=_release/VERSION/doc/$name.html

  local meta=${prefix}_meta.json 
  cat >$meta <<EOF
{ "title": "$title",
  "repo_url": "$src",
  "css_files": "$css_files",
  "all_docs_url": ".",

  "build_timestamp": "$TIMESTAMP",
  "oil_version": "$OIL_VERSION"
}
EOF

  cmark $meta $src > $out
  log "Wrote $out"
}

special() {
  render-only 'README.md' '../web/manual.css ../web/toc.css' 'Oil Source Code'
  render-only 'INSTALL.txt' '../web/install.css' 'Installing Oil'

  split-and-render doc/release-index.md _tmp/release-index.html
}

all-markdown() {
  mkdir -p _tmp/doc

  # TODO: We can set repo_url here!  Then we don't need it for most docs.
  # split_doc.py can return {} if the doc doesn't start with ---

  #for d in doc/index.md doc/known-differences.md doc/*-manual.md \
  #  doc/eggex.md doc/oil-options.md doc/oil-func-proc-block.md; do
  for d in "${MARKDOWN_DOCS[@]}"; do
    split-and-render doc/$d.md
  done

  special
}

# TODO: This could use some CSS.
man-page() {
  local root_dir=${1:-_release/VERSION}
  mandoc -T html doc/osh.1 > $root_dir/osh.1.html
  ls -l $root_dir
}

# I want to ship the INSTALL file literally, so just mutate things
_sed-ext() {
  sed --regexp-extended -i "$@"
}

update-src-versions() {
  _sed-ext \
    "s/[0-9]+\.[0-9]+\.[a-z0-9]+/$OIL_VERSION/g" \
    doc/release-index.md 

  _sed-ext \
    "s/oil-[0-9]+\.[0-9]+\.[a-z0-9]+/oil-$OIL_VERSION/g" INSTALL.txt

  _sed-ext \
    "s;/release/[0-9]+\.[0-9]+\.[a-z0-9]+/;/release/$OIL_VERSION/;g" \
    doc/osh.1
}

oil-grammar() {
  PYTHONPATH=. oil_lang/cmd_parse.py "$@"
}

important-source-code() {
  local dest=_tmp/important-source-code
  mkdir -p $dest

  for rel_path in \
    frontend/lex.py \
    _devbuild/tmp/osh-lex.re2c.h \
    _devbuild/gen/osh-lex.h \
    _devbuild/gen/id.h \
    frontend/syntax.asdl \
    oil_lang/grammar.pgen2; do
  mkdir -p $dest/$(dirname $rel_path)
    cp --no-target-directory -v $rel_path $dest/$rel_path
  done
}

#
# Test Tools
#

split-doc-demo() {
  cat > _tmp/testdoc.md <<EOF
---
title: foo
---

Title
=====

hello

EOF

  devtools/split_doc.py _tmp/testdoc.md _tmp/testdoc

  head _tmp/testdoc*
}

make-help-demo() {
  devtools/make_help.py text-index <<EOF

<h2 id="intro">Intro</h2>
<pre class="help-index">
  [Usage]         bundle-usage   osh-usage   oil-usage   config   startup
                  line-editing   prompt
  [Lexing]        comments #   line-continuation \\
  [Oil Lexing]    single-command %%%   docstring ###
</pre>

<p>foo &amp; bar</p>

<h2 id="cmd">Command Language</h2>

EOF
}

#
# Help is both markdown and text
#

# Generate an HTML page for the help index.  It has an extra step.
help-index-html() {
  # TODO: split the doc
  # Run through devtools/cmark.py?
  # And then parse the <pre> sections?

  #devtools/make_help.py html-index < doc/help-index.md

  local tmp=_tmp/help-index.html
  split-and-render doc/help-index.md $tmp

  ls -l $tmp

  local out=_release/VERSION/doc/help-index.html
  devtools/make_help.py html-index < $tmp > $out

  ls -l $out
}

readonly TEXT_DIR=_devbuild/help
readonly HTML_DIR=_release/VERSION
readonly CODE_DIR=_devbuild/gen

# NOTE: Should eventually take .html instead of .md
help-index-text() {
  local out_dir=${1:-_devbuild/help}

  local py_out=$CODE_DIR/help_index.py
  devtools/make_help.py text-index $out_dir $py_out < doc/help-index.md
}

help-cards() {
  ### Do all cards at once

  # Pass the HTML.  This makes it easier to parse headings
  #devtools/make_help.py cards \
  #  $HTML_DIR/doc/help.html $HTML_DIR/doc/help-index.html $TEXT_DIR

  local py_out=$CODE_DIR/help_.py

  # For now, the pass help markdown
  devtools/make_help.py cards \
    doc/help.md $HTML_DIR/doc/help-index.html $TEXT_DIR $py_out
}

all-help() {
  mkdir -p $TEXT_DIR
  rm -v -f $TEXT_DIR/*

  help-index-html $HTML_DIR
  log 'index text done'

  split-and-render doc/help.md

  help-index-text $TEXT_DIR $CODE_DIR
  help-cards $HTML_DIR $TEXT_DIR

  # Better sorting
  LANG=C ls -l $TEXT_DIR
}

minimal-help() {
  ### for build/dev.sh minimal

  mkdir -p $TEXT_DIR
  rm -v -f $TEXT_DIR/*

  help-index-text $TEXT_DIR $CODE_DIR
  help-cards $HTML_DIR $TEXT_DIR
}

run-for-release() {
  all-markdown
  all-help
}

"$@"
