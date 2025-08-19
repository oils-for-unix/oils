#!/usr/bin/env bash
#
# Build docs
#
# Usage:
#   build/doc.sh <function name>
#
# Examples:
#
#   make HTML:
#     $0 split-and-render doc/json.md
#     $0 split-and-render doc/ref/chap-type-method.md '' ../../web  # need relative URL
#
#   check code in a doc:
#     $0 run-code-in-doc ysh-io 
#     $0 run-code-in-doc ref/chap-type-method
#
#     $0 run-code-all  # check all code
#
#   build docs:
#     $0 all-ref
#     $0 all-markdown

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

readonly OILS_VERSION=$(head -n 1 oils-version.txt)
export OILS_VERSION  # for quick_ref.py

THIS_DIR=$(readlink -f $(dirname $0))
readonly THIS_DIR
REPO_ROOT=$(cd $THIS_DIR/.. && pwd)
readonly REPO_ROOT


readonly HTML_BASE_DIR=_release/VERSION


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

# Places version is used
#
# - in --version
# - in URL for every page?  inside the binary
# - in titles for index, install, osh-quick-ref TOC, etc.
# - in deployment script

# Run with environment variable
help-gen() {
  PYTHONPATH=.:vendor doctools/help_gen.py "$@"
}

cmark() {
  # h2 and h3 are shown in TOC.  The blog uses "legacy" h3 and h4.
  PYTHONPATH=.:vendor doctools/cmark.py --toc-tag h2 --toc-tag h3 --toc-pretty-href "$@"
}

readonly MARKDOWN_DOCS=(
  published

  # polished
  getting-started
  portability
  known-differences
  ysh-error
  error-handling
  error-catalog
  json
  hay
  simple-word-eval
  quirks
  warts

  eggex
  ysh-regex-api
  upgrade-breakage
  ysh-tour
  ysh-io

  style-guide
  novelties

  proc-func
  block-literals
  objects
  types

  pure-mode

  # Data language
  qsn
  qtt
  j8-notation
  htm8
  # Protocol
  pretty-printing
  stream-table-process
  byo
  ysh-doc-processing

  table-object-doc

  lib-osh

  doc-toolchain
  doc-plugins
  ul-table
  ul-table-compare
  idioms
  shell-idioms
  ysh-faq

  language-influences
  ysh-vs-python
  ysh-vs-shell

  syntactic-concepts
  syntax-feelings
  command-vs-expression-mode

  repo-overview

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
# I believe --rfc-email should never output a Unicode character.
#
# A better fix would be to implement json_utf8.load(f), which doesn't decode
# into unicode instances.  This would remove useless conversions.

default-doc-timestamp() {
  # Note: this flag doesn't exist on Alpine Linux
  if ! date --rfc-email; then
    echo '(error: No DOC_TIMESTAMP and no date --rfc-e-mail)'
  fi
}

DOC_TIMESTAMP=${DOC_TIMESTAMP:-$(default-doc-timestamp)}

split-and-render() {
  local src=${1:-doc/known-differences.md}

  local rel_path=${src%'.md'}  # doc/known-differences
  local tmp_prefix=_tmp/$rel_path  # temp dir for splitting

  local out=${2:-$HTML_BASE_DIR/$rel_path.html}
  local web_url=${3:-'../web'}
  local quiet=${4:-}

  mkdir -v -p $(dirname $out) $tmp_prefix

  # Also add could add css_files.  The one in the file takes precedence always?

  # css_files: a space-separated list
  # all_docs_url: so we link from doc/foo.html -> doc/

  local css_files="$web_url/base.css $web_url/manual.css $web_url/toc.css $web_url/language.css $web_url/code.css"

  PYTHONPATH='.:vendor' doctools/split_doc.py \
    -v build_timestamp="$DOC_TIMESTAMP" \
    -v oil_version="$OILS_VERSION" \
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

  if test -z "$quiet"; then
    log "$tmp_prefix -> (doctools/cmark) -> $out"
  fi
}

render-from-kate() {
  ### Make it easier to configure Kate editor

  # It want to pass an absolute path
  # TODO: I can't figure out how to run this from Kate?

  local full_path=$1

  case $full_path in
    $REPO_ROOT/*)
      rel_path=${full_path#"$REPO_ROOT/"}
      echo "relative path = $rel_path"
      ;;
    *)
      die "$full_path should start with repo root $REPO_ROOT"
      ;;
  esac

  split-and-render $rel_path
}

# Special case for README
# Do NOT split because we don't want front matter in the markdown source.
render-only() {
  local src=${1:-README.md}

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

  local out=${2:-$HTML_BASE_DIR/doc/$name.html}
  local css_files=${3:-'../web/manual.css ../web/toc.css'}
  local title=${4:-'Oils Source Code'}

  local prefix=_tmp/doc/$name

  local meta=${prefix}_meta.json 
  cat >$meta <<EOF
{ "title": "$title",
  "repo_url": "$src",
  "css_files": "$css_files",
  "all_docs_url": ".",

  "build_timestamp": "$DOC_TIMESTAMP",
  "oil_version": "$OILS_VERSION"
}
EOF

  cmark $meta $src > $out
  log "Wrote $out"
}

help-mirror-md() {
  echo '
Oils Build `--help` Mirror
=====

<style>
/* Similar to web/install.css */
h1 { font-size: 1.5em; }
h2 { font-size: 1.2em; }

/* Exclude Markdown <pre><code> */
code:not(pre code) {
  color: green;
}
</style>

This doc mirrors the `--help` for the 3 shell tools in the build system:

1. `configure` - Detect system features
1. `_build/oils.sh` - Compile `oils-for-unix` source into an executable
1. `install` - Install the executable, and symlinks to it

We also provide a tiny script to statically link the `oils-for-unix` binary.

<div id="toc">
</div>

## Note: Usage is Different Than Autotools

To minimize build deps, all 3 of these tools are hand-written POSIX shell
scripts.  So this build system does **not** use GNU autotools, and it does not
use `make`.

Keep these differences in mind:

- Settings are configured with **either** flags or env vars, as described
  below.
  - For example, use `./configure --cxx-for-configure mycc`, not `CXX=mycc
  configure`.
- If you pass `./configure --cxx-for-configure mycc`, you should also pass
  `_build/oils.sh --cxx mycc`.  The flag value is not remembered.

## configure

```'
  ./configure --help

  echo '```

## _build/oils.sh

```'

  devtools/release-native.sh gen-shell-build
  _build/oils.sh --help

  echo '```

## install

```'
  ./install --help
  echo '```

## build/static-oils.sh

```'
  build/static-oils.sh --help
  echo '```

## Links

- [INSTALL.html](INSTALL.html) - Quick guide for end users.
- [Oils Packaging Guidelines]($wiki) wiki
- [Oils Packaging Tips]($wiki) wiki - free free to edit this page.

  '
}

help-mirror() {
  ### Mirror --help to HTML

  local md=_tmp/doc/help-mirror.md

  help-mirror-md > $md

  local web_dir='../web'
  #local css="$web_dir/base.css $web_dir/install.css $web_dir/toc.css" 
  local css="$web_dir/base.css $web_dir/toc.css" 
  render-only $md '' "$css" 'Oils Build Help Mirror'
}

special() {
  # TODO: do all READMEs
  split-and-render mycpp/README.md \
    $HTML_BASE_DIR/doc/oils-repo/mycpp/README.html \
    ../../../web

  # TODO: README can just be a pointer to other docs, like "Repo Overview"
  local web_dir='../../web'
  render-only 'README.md' $HTML_BASE_DIR/doc/oils-repo/README.html \
    "$web_dir/base.css $web_dir/manual.css $web_dir/toc.css" 'Oils Source Code'

  help-mirror

  local web_dir='../web'
  render-only INSTALL.txt '' \
    "$web_dir/base.css $web_dir/install.css" 'Installing Oils'

  render-only INSTALL-old.txt '' \
    "$web_dir/base.css $web_dir/install.css" 'Installing Oils - old CPython build'

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
ysh-help ref/toc-ysh
ysh-help-topics ref/toc-ysh
EOF
}

all-redirects() {
  log '*** Writing redirects'
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
  # Update tarball names, etc.
  _sed-ext \
    "s/[0-9]+\.[0-9]+\.[a-z0-9]+/$OILS_VERSION/g" \
    doc/release-*.md INSTALL.txt INSTALL-old.txt README-native.txt

  # Update /release/0.8.4/ URL, etc.
  _sed-ext \
    "s;/release/[0-9]+\.[0-9]+\.[a-z0-9]+/;/release/$OILS_VERSION/;g" \
    doc/osh.1
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
  help-gen ref-check \
    doc/ref/toc-*.md \
    _release/VERSION/doc/ref/chap-*.html 
}

fmt-check() {
  PYTHONPATH=.:vendor doctools/fmt_check.py _release/VERSION/doc/ref/*.html
}


write-metrics() {
  ### Check indexes and chapters against each other

  local out=_release/VERSION/doc/metrics.txt

  log '*** ref-check'

  # send stderr to the log file too
  ref-check > $out 2>&1

  echo "Wrote $out"
}

maybe-tree() {
  if command -v tree >/dev/null; then
    tree $work_dir
  fi
}

ysh-tour() {
  ### Build the Tour of YSH, and execute code as validation
  local name=${1:-ysh-tour}

  split-and-render doc/$name.md

  local work_dir=$REPO_ROOT/_tmp/ysh-tour
  mkdir -p $work_dir
  pushd $work_dir

  mkdir -p lib

  # Files used by module example
  touch {build,test}.sh

  cat >lines.txt <<'EOF'
  doc/hello.md
 "doc/with spaces.md"
b'doc/with byte \yff.md'
EOF
  
  cat >myargs.ysh <<EOF
const __provide__ = :| proc1 p2 p3 |

proc proc1 {
  echo proc1
}

proc p2 {
  echo p2
}

proc p3 {
  echo p3
}
EOF

  cat >demo.py <<EOF
#!/usr/bin/env python

print("hi")
EOF
  chmod +x demo.py

  cat >lib/util.ysh <<EOF
const __provide__ = :| log |

proc log {
  echo @ARGV >&2
}
EOF

  local code_dir=$REPO_ROOT/_tmp/code-blocks/doc

  # Prepend extra code
  cat >tour.ysh - $code_dir/$name.txt <<EOF
func myMethod(self) {
  echo 'myMethod'
}

func mutatingMethod(self) {
  echo 'mutatingMethod'
}

func makeMyObject(x) {
  var methods = Object(null, {myMethod, 'M/mutatingMethod': mutatingMethod})
  return (Object(methods, {x}))
}
EOF

  # Fix: don't supply stdin!
  $REPO_ROOT/bin/ysh tour.ysh < /dev/null
  popd

  maybe-tree $work_dir

  # My own dev tools
  # if test -d ~/vm-shared; then
  if false; then
    local path=_release/VERSION/doc/$name.html
    cp -v $path ~/vm-shared/$path
  fi
}

run-code-in-doc() {
  local name=${1:-'ysh-io'}

  local web_url
  case $name in 
    ref/*)
      web_url='../../web'
      ;;
    *)
      web_url='../web'
      ;;
  esac

  set -x
  split-and-render doc/$name.md '' $web_url

  local work_dir=$REPO_ROOT/_tmp/$name
  rm -r -f "$work_dir"
  mkdir -p $work_dir

  pushd $work_dir

  local code_dir=$REPO_ROOT/_tmp/code-blocks/doc

  mkdir -p ref
  cp $code_dir/$name.txt $name.ysh

  #$REPO_ROOT/bin/ysh $name.ysh
  $REPO_ROOT/bin/ysh -x $name.ysh

  maybe-tree $work_dir

  popd
}

run-code-all() {
  run-code-in-doc 'ysh-io'
  run-code-in-doc 'ref/chap-type-method'

  # TODO: add more docs here
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

indices-chapters() {

  log "Building doc/ref"
  local -a sources=( doc/ref/*.md )
  local -A pid_map=()
  for d in ${sources[@]}; do 
    # do ~23 docs in parallel; this saves more than one second on my machine
    split-and-render $d '' '../../web' QUIET &
    pid_map[$!]=$d
  done

  local failed=''
  for pid in "${!pid_map[@]}"; do
    #echo "WAIT $pid"

    # Funny dance to get exit code
    set +o errexit
    wait $pid
    status=$?
    set -o errexit

    if test $status -ne 0; then
      local d=${pid_map[$pid]}
      echo
      echo "*** Building '$d' failed ***"
      echo
      failed=T
    fi
  done

  if test -n "$failed"; then
    return 1
  fi
}

all-ref() {
  ### Build doc/ref in text and HTML.  Depends on libcmark.so

  rm -f $TEXT_DIR/*
  make-dirs

  indices-chapters

  # Note: if we want a $ref-topic shortcut, we might want to use Ninja to
  # extract topics from all chapters first, and then make help_meta.json, like
  # we have _devbuild/gen/help_meta.py.

  # Text cards
  cards-from-indices  # 3 help_gen.py processes
  # A few text cards, and HELP_TOPICS dict for URLs, for flat namespace
  cards-from-chapters  # 1 help_gen.py process

  return

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

  # We switched to .gz for oils-for-unix
  # Note: legacy names are needed for old releases
  for name in \
    oils-for-unix-$version.tar.{gz,xz} \
    oils-ref-$version.tar.gz \
    oil-$version.tar.{gz,xz} \
    oil-native-$version.tar.xz; do

    local url="/download/$name"  # The server URL
    local path="../oils.pub__deploy/download/$name"

    # Don't show tarballs that don't exist
    if ! test -f "$path"; then
      case $name in
        oils-for-unix-*|oil-native-*)
          ;;
        *)
          log "Warning: Expected tarball $name to exist"
          ;;
      esac
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
  tarball-links-row-html "$OILS_VERSION"
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

patch-release-pages() {
  local release_date
  release_date=$(cat _build/release-date.txt)

  local root=_release/VERSION

  add-date-and-links $release_date < _tmp/release-index.html > $root/index.html
  add-date-and-links $release_date < _tmp/release-quality.html > $root/quality.html
}

copy-release-pages() {
  ### For testing without releasing

  cat < _tmp/release-index.html > $root/index.html
  cat < _tmp/release-quality.html > $root/quality.html
}

run-for-release() {
  ### Build a tree.  Requires _build/release-date.txt to exist

  local root=_release/VERSION
  mkdir -p $root/{doc,test,pub}

  ysh-tour
  run-code-all

  # Metadata
  cp -v _build/release-date.txt oils-version.txt $root

  # Docs
  # Writes _release/VERSION and _tmp/release-index.html
  all-markdown
  all-ref
  all-redirects  # backward compat

  fmt-check  # Needs to run *after* we build the HTML

  patch-release-pages

  write-metrics

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

#
# Generator
#

_gen-readme-index() {
  # Use relative markdown links
  echo '
Oils Repo READMEs
=================

This page is useful for finding docs that are out of date.

Generate it with:

    build/doc.sh gen-readme-index

'
  for path in */README.md; do
    echo "- [$path]($path)"
  done
}

gen-readme-index() {
  _gen-readme-index > README-index.md
}

#
# Golden tests
#
# $0 golden-tree
# $0 determinstic-build  # with new code
# $0 compare-golden

deterministic() {
  # build without varying timestamp
  DOC_TIMESTAMP='GOLD' $0 soil-run
}

golden-tree() {
  rm -r -f _release/VERSION/ _release/VERSION_gold/
  deterministic
  cp -r _release/VERSION/ _release/VERSION_gold
}

compare-golden() {
  diff -r -u _release/VERSION_gold _release/VERSION/ 
}

task-five "$@"

