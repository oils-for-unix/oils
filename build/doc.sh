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
help-gen() {
  PYTHONPATH=. doctools/help_gen.py "$@"
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
  error-handling
  json
  hay
  simple-word-eval
  quirks
  warts

  eggex
  ysh-regex-api
  upgrade-breakage
  ysh-tour

  style-guide
  novelties

  proc-func
  block-literals

  # Data language
  qsn
  qtt
  j8-notation

  doc-toolchain
  doc-plugins
  idioms
  shell-idioms
  ysh-faq

  language-influences
  ysh-vs-python
  ysh-vs-shell

  syntactic-concepts
  syntax-feelings
  command-vs-expression-mode

  # needs polish
  # Note: docs about the YSH are prefixed 'ysh-'.
  # data-model and command-vs-expression-mode span both OSH and YSH

  index
  faq-doc

  options

  old/index
  old/project-tour
  old/legacy-array
  old/ysh-keywords
  old/modules
  old/expression-language
  old/word-language
  old/errors
  old/ysh-builtins

  io-builtins
  unicode
  framing
  xtrace
  headless
  completion
  strings
  variables

  # Internal stuff
  interpreter-state
  process-model
  architecture-notes
  parser-architecture
)

# Bug fix: Plain $(date) can output unicode characters (e.g. in Japanese
# locale), which is loaded by Python into say u'\u5e74'.  But the default
# encoding in Python 2 is still 'ascii', which means that '%s' % u_str may
# fail.
#
# I believe --rfc-e-mail should never output a Unicode character.
#
# A better fix would be to implement json_utf8.load(f), which doesn't decode
# into unicode instances.  This would remove useless conversions.

readonly TIMESTAMP=$(date --rfc-email)

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

  # for ysh-tour code blocks
  local code_out=_tmp/code-blocks/$rel_path.txt
  mkdir -v -p $(dirname $code_out)

  cmark \
    --code-block-output $code_out \
    ${tmp_prefix}_meta.json ${tmp_prefix}_content.md > $out

  log "$tmp_prefix -> (doctools/cmark) -> $out"
}

# Special case for README
# Do NOT split because we don't want front matter in the markdown source.
render-only() {
  local src=${1:-README.md}
  local css_files=${2:-'../web/manual.css ../web/toc.css'}
  local title=${3:-'Oils Source Code'}

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
  render-only 'README.md' '../web/base.css ../web/manual.css ../web/toc.css' 'Oils Source Code'
  render-only 'INSTALL.txt' '../web/base.css ../web/install.css' 'Installing Oils'

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
  PYTHONPATH=. ysh/cmd_parse.py "$@"
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

cards-from-indices() {
  ### Make help cards

  for lang in osh ysh data; do
    help-gen cards-from-index $lang $TEXT_DIR \
      < $HTML_DIR/doc/ref/toc-$lang.html
  done
}

cards-from-chapters() {
  ### Turn h3 topics into cards

  local py_out=$CODE_DIR/help_meta.py

  mkdir -p _gen/frontend
  local cc_prefix=_gen/frontend/help_meta

  help-gen cards-from-chapters $TEXT_DIR $py_out $cc_prefix \
    $HTML_DIR/doc/ref/chap-*.html
}

ref-check() {
  ### Check indexes and chapters against each other

  help-gen ref-check \
    doc/ref/toc-*.md \
    _release/VERSION/doc/ref/chap-*.html
}

tour() {
  ### Build the Tour of YSH, and execute code as validation
  local name=${1:-ysh-tour}

  split-and-render doc/$name.md

  local work_dir=$REPO_ROOT/_tmp/code-blocks/doc

  mkdir -p $work_dir/lib

  # Files used by module example
  touch $work_dir/{build,test}.sh

  cat >$work_dir/lib/util.ysh <<EOF
log() { echo "$@" 1>&2; }
EOF

  pushd $work_dir
  $REPO_ROOT/bin/ysh $name.txt
  popd

  # My own dev tools
  if test -d ~/vm-shared; then
    local path=_release/VERSION/doc/$name.html
    cp -v $path ~/vm-shared/$path
  fi
}

one() {
  ### Iterate on one doc quickly

  local name=${1:-options}

  split-and-render doc/$name.md

  # Make sure the doc has valid YSH code?
  # TODO: Maybe need an attribute for OSH or YSH
  pushd _tmp/code-blocks/doc
  $REPO_ROOT/bin/ysh $name.txt
  popd

  if test -d ~/vm-shared; then
    local out="${name%.md}.html"
    local path=_release/VERSION/$out
    cp -v $path ~/vm-shared/$path
  fi
}

make-dirs() {
  mkdir -p $TMP_DIR $CODE_BLOCK_DIR $TEXT_DIR $HTML_DIR/doc
}

one-ref() {
  local md=${1:-doc/ref/index.md}
  split-and-render $md '' '../../web'
}

all-ref() {
  ### Build doc/ref in text and HTML.  Depends on libcmark.so

  log "Removing $TEXT_DIR/*"
  rm -f $TEXT_DIR/*
  make-dirs

  # Make the indexes and chapters
  for d in doc/ref/*.md; do
    split-and-render $d '' '../../web'
  done

  # Text cards
  cards-from-indices
  # A few text cards, and HELP_TOPICS dict for URLs, for flat namespace
  cards-from-chapters

  if command -v pysum; then
    # 19 KB of embedded help, seems OK.  Biggest card is 'ysh-option'.  Could
    # compress it.
    echo 'Size of embedded help:'
    ls -l $TEXT_DIR | tee /dev/stderr | awk '{print $5}' | pysum
  fi

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

  tour

  # Metadata
  cp -v _build/release-date.txt oil-version.txt $root

  # Docs
  # Writes _release/VERSION and _tmp/release-index.html
  all-markdown
  all-ref
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
  build/stamp.sh write-release-date

  run-for-release
}

"$@"

