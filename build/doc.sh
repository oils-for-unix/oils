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

THIS_DIR=$(readlink -f $(dirname $0))
readonly THIS_DIR
REPO_ROOT=$(cd $THIS_DIR/.. && pwd)
readonly REPO_ROOT


log() {
  echo "$@" 1>&2
}

#
# Deps (similar to doctools/cmark.sh and build/codegen.sh)
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
  PYTHONPATH=. doctools/make_help.py "$@"
}

cmark() {
  # h2 and h3 are shown in TOC.  The blog uses "legacy" h3 and h4.
  PYTHONPATH=. doctools/cmark.py --toc-tag h2 --toc-tag h3 --toc-pretty-href "$@"
}

readonly MARKDOWN_DOCS=(
  # Help index has its own rendering

  # polished
  getting-started
  known-differences
  errors
  error-handling
  json
  hay
  simple-word-eval
  quirks
  warts
  variables
  eggex
  upgrade-breakage
  qsn

  doc-toolchain
  doc-plugins
  idioms
  shell-idioms
  ysh-faq
  qtt
  language-influences
  oil-vs-python
  oil-vs-shell
  syntactic-concepts
  syntax-feelings

  # needs polish
  # Note: docs about the Oil language are prefixed 'oil-'.
  # data-model and command-vs-expression-mode span both OSH and Oil.

  index
  faq-doc

  project-tour
  ysh-tour

  options
  oil-keywords
  oil-builtins
  command-vs-expression-mode

  command-language
  expression-language
  word-language

  oil-special-vars
  proc-block-func
  io-builtins
  unicode
  framing
  xtrace
  headless
  completion
  strings
  modules

  # Internal stuff
  variable-scope
  interpreter-state
  process-model
  architecture-notes
  parser-architecture
)

readonly TIMESTAMP=$(date)

split-and-render() {
  local src=${1:-doc/known-differences.md}

  local rel_path=${src%'.md'}  # doc/known-differences
  local tmp_prefix=_tmp/$rel_path  # temp dir for splitting

  local out=${2:-_release/VERSION/$rel_path.html}
  local web_url=${3:-'../web'}

  mkdir -v -p $(dirname $out) $tmp_prefix

  # Also add could add css_files.  The one in the file takes precedence always?

  # css_files: a space-separated list
  # all_docs_url: so we link from doc/foo.html -> doc/

  local css_files="$web_url/base.css $web_url/manual.css $web_url/toc.css $web_url/language.css $web_url/code.css"

  doctools/split_doc.py \
    -v build_timestamp="$TIMESTAMP" \
    -v oil_version="$OIL_VERSION" \
    -v css_files="$css_files" \
    -v all_docs_url='.' \
    -v repo_url="$src" \
    $src $tmp_prefix

  #ls -l _tmp/doc
  #head _tmp/doc/*
  #return

  local code_out=_tmp/code-blocks/$rel_path.txt
  mkdir -v -p $(dirname $code_out)

  cmark --code-block-output $code_out ${tmp_prefix}_meta.json ${tmp_prefix}_content.md > $out
  log "$tmp_prefix -> (doctools/cmark) -> $out"
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
  render-only 'README.md' '../web/base.css ../web/manual.css ../web/toc.css' 'Oil Source Code'
  render-only 'INSTALL.txt' '../web/base.css ../web/install.css' 'Installing Oil'

  # These pages aren't in doc/
  split-and-render doc/release-index.md _tmp/release-index.html
  split-and-render doc/release-quality.md _tmp/release-quality.html
}

all-markdown() {
  make-dirs

  # TODO: We can set repo_url here!  Then we don't need it for most docs.
  # split_doc.py can return {} if the doc doesn't start with ---

  #for d in doc/index.md doc/known-differences.md doc/*-manual.md \
  #  doc/eggex.md doc/oil-options.md doc/oil-func-proc-block.md; do
  for d in "${MARKDOWN_DOCS[@]}"; do
    split-and-render doc/$d.md
  done

  special
}

redir-body() {
  local to_url=$1  # WARNING: no escaping
  cat <<EOF
<head>
  <meta http-equiv="Refresh" content="0; URL=$to_url" />
</head>
EOF
}

redirect-pairs() {
  # we want want /release/latest/ URLs to still work
  cat <<EOF
oil-language-tour ysh-tour
oil-language-faq ysh-faq
oil-help ysh-help
oil-help-topics ysh-help-topics
EOF
}

all-redirects() {
  redirect-pairs | while read -r from_page to_page; do
    redir-body "$to_page.html" | tee "_release/VERSION/doc/$from_page.html"
  done
}

all-ref() {
  for d in doc/ref/*.md; do
    split-and-render $d '' '../../web'
  done
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
    doc/release-*.md

  # we need to update tarball paths, /release/0.8.4/ URL, etc.
  _sed-ext \
    "s/[0-9]+\.[0-9]+\.[a-z0-9]+/$OIL_VERSION/g" INSTALL.txt

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
    frontend/lexer_def.py \
    _build/tmp/frontend/match.re2c.txt \
    _gen/frontend/match.re2c.h \
    _gen/frontend/id_kind.asdl_c.h \
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

  doctools/split_doc.py _tmp/testdoc.md _tmp/testdoc

  head _tmp/testdoc*
}

#
# Help is both markdown and text
#

readonly TMP_DIR=_tmp/doc
readonly CODE_BLOCK_DIR=_tmp/code-blocks
readonly TEXT_DIR=_devbuild/help
readonly HTML_DIR=_release/VERSION
readonly CODE_DIR=_devbuild/gen

# TODO:
# - change to sh- vs oil- prefix, e.g. for arith

help-topics() {
  _make-help topics > $TEXT_DIR/osh < $HTML_DIR/doc/osh-help-topics.html
  _make-help topics > $TEXT_DIR/ysh < $HTML_DIR/doc/ysh-help-topics.html
}

help-cards() {
  ### Do all cards at once

  local py_out=$CODE_DIR/help_.py

  # TODO: We need to re-indent <code> blocks here, etc.

  _make-help cards $TEXT_DIR $py_out \
    $HTML_DIR/doc/osh-help.html $HTML_DIR/doc/ysh-help.html
}

tour() {
  ### Build the Oil Language Tour and execute code
  local name=${1:-ysh-tour}

  split-and-render doc/$name.md

  local work_dir=$REPO_ROOT/_tmp/code-blocks/doc

  # Files used by module example
  touch $work_dir/{build,test}.sh

  mkdir -p $work_dir/lib
  cat >$work_dir/lib/util.oil <<EOF
log() { echo "$@" 1>&2; }
EOF

  pushd $work_dir
  $REPO_ROOT/bin/oil $name.txt
  popd

  # My own dev tools
  if test -d ~/vm-shared; then
    local path=_release/VERSION/doc/$name.html
    cp -v $path ~/vm-shared/$path
  fi
}

one() {
  ### Iterate on one doc quickly

  local doc=${1:-doc/oil-vs-python.md}

  split-and-render $doc

  if test -d ~/vm-shared; then
    local out="${doc%.md}.html"
    local path=_release/VERSION/$out
    cp -v $path ~/vm-shared/$path
  fi
}

make-dirs() {
  mkdir -p $TMP_DIR $CODE_BLOCK_DIR $TEXT_DIR $HTML_DIR/doc
}

all-help() {
  ### Build HTML and text help, which depends on libcmark.so

  log "Removing $TEXT_DIR/*"
  rm -f $TEXT_DIR/*
  make-dirs

  split-and-render doc/ysh-help-topics.md
  split-and-render doc/ysh-help.md
  split-and-render doc/osh-help-topics.md
  split-and-render doc/osh-help.md

  #help-index-cards
  help-topics
  help-cards

  # Better sorting
  #LANG=C ls -l $TEXT_DIR
}

_copy-path() {
  local src=$1 dest=$2
  mkdir -p $(dirname $dest)
  cp -v $src $dest
}

copy-web() {
  find web \
    \( -name _tmp -a -prune \) -o \
    \( -name '*.css' -o -name '*.js' \) -a -printf '%p _release/VERSION/%p\n' |
  xargs -n 2 -- $0 _copy-path
}

pretty-size() {
  local path=$1
  stat --format '%s' "$path" | python -c '
import sys
num_bytes = int(sys.stdin.read())
print "{:,}".format(num_bytes)
'
}

# NOTE: It might be better to link to files like this in the /release/ tree.
# Although I am not signing them.

# https://nodejs.org/dist/v8.11.4/SHASUMS256.txt.asc

tarball-links-row-html() {
  local version=$1

  cat <<EOF
<tr class="file-table-heading">
  <td></td>
  <td>File / SHA256 checksum</td>
  <td class="size">Size</td>
  <td></td>
</tr>
EOF

  # we switched to .gz for oils for Unix
  for name in oil-$version.tar.{gz,xz} \
    oils-for-unix-$version.tar.{gz,xz} \
    oil-native-$version.tar.xz; do

    local url="/download/$name"  # The server URL
    local path="../oilshell.org__deploy/download/$name"

    # Don't show tarballs that don't exist
    if [[ $name == oils-for-unix-* && ! -f $path ]]; then
      continue
    fi
    if [[ $name == oil-native-* && ! -f $path ]]; then
      continue
    fi

    local checksum
    checksum=$(sha256sum $path | awk '{print $1}')
    local size
    size=$(pretty-size $path)

    # TODO: Port this to oil with "commas" extension.

    # Three columns: date, version, and links
    cat <<EOF
    <tr> 
      <td></td>
      <td class="filename"><a href="$url">$name</a></td>
      <td class="size">$size</td>
    </tr>
    <tr>
      <td></td>
      <td colspan=2 class="checksum">$checksum</td>
    </tr>
EOF
  done
}

this-release-links() {
  echo '<div class="file-table">'
  echo '<table>'
  tarball-links-row-html "$OIL_VERSION"
  echo '</table>'
  echo '</div>'
}

# Turn HTML comment into a download link
add-date-and-links() {
  local snippet
  snippet=$(this-release-links)

  awk -v date=$1 -v snippet="$snippet" '
    /<!-- REPLACE_WITH_DOWNLOAD_LINKS -->/ {
      print(snippet)
      next
    }

    /<!-- REPLACE_WITH_DATE -->/ {
      print(date)
      next
    }

    # Everything else
    { print }
  '
}

modify-pages() {
  local release_date
  release_date=$(cat _build/release-date.txt)

  local root=_release/VERSION

  add-date-and-links $release_date < _tmp/release-index.html > $root/index.html
  add-date-and-links $release_date < _tmp/release-quality.html > $root/quality.html
}

run-for-release() {
  ### Build a tree.  Requires _build/release-date.txt to exist

  local root=_release/VERSION
  mkdir -p $root/{doc,test,pub}

  # Metadata
  cp -v _build/release-date.txt oil-version.txt $root

  # Docs
  # Writes _release/VERSION and _tmp/release-index.html
  all-markdown
  all-help
  all-redirects  # backward compat

  modify-pages

  # Problem: You can't preview it without .wwz!
  # Maybe have local redirects VERSION/test/wild/ to 
  #
  # Instead of linking, I should compress them all here.

  copy-web

  if command -v tree >/dev/null; then
    tree $root
  else
    find $root
  fi
}

soil-run() {
  build/ovm-actions.sh write-release-date

  run-for-release
}

"$@"

