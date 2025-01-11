#!/usr/bin/env bash
#
# Usage:
#   data_lang/htm8-test.sh
#
# TODO:
# - Refactor Validate(): take FLAGS, return stats optionally
#   - add LEX_QUOTED_VALUES
#   - and then re-run all the tests
# - Rename to data_lang/htm8.py
#   - it has NO_SPECIAL_TAGS mode for XML
#
# - Soil
#   - Validate all the HTML in the repo - well-formed check
#     - this should go in the CI
#   - Automate some more tests:
#     - site oils.pub, site oilshell.org
#     - XML on my machine - turn that in to 'WILD' corpus for HTML/XML?
#
# - statically type it
#   - revive pyannotate
# - translate to C++
#   - what to do about all the regexes?  Port to re2c directly?
#   - for find(), do we need a C++ primitive for it?
#   - no allocation for TagName()
#   - ASDL file for Tok.Foo?
# - refactor TagName() API - remove it from the TagLexer?
#   - that is really the AttrLexer()
#
# - build a DOM with objects in YSH?
#   - rewrite ul-table in that?
#
# YSH API
# - Generating HTML/HTM8 is much more common than parsing it
#   - although maybe we can do RemoveComments as a demo?
#   - that is the lowest level "sed" model
# - For parsing, a minimum idea is:
#   - lexer-based algorithms for query by tag, class name, and id
#   - and then toTree()
#     - .tag and .attrs?
#     - .innerHTML() and .outerHTML() perhaps
#     - and maybe you can mutate it directly

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

# Special case: we need $REPO_ROOT
: ${LIB_OSH=$REPO_ROOT/stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

# parse with lazylex/html.py, or data_lang/htm8.py

site-files() {
  #find ../../oilshell/oilshell.org__deploy -name '*.html'

  # omit all the _ files
  git ls-files | grep '\.html$'
}

# Issues with lazylex/html.py
# 
# - Token ID is annoying to express in Python
# - re.DOTALL for newlines
#   - can we change that with [.\n]*?
# - nongreedy match for --> and ?>

htm8-tool() {
  PYTHONPATH="$REPO_ROOT:$REPO_ROOT/vendor" \
    $REPO_ROOT/lazylex/html.py "$@"
}

test-well-formed() {
  cat >_tmp/bad.html <<EOF
unfinished <!--
hi && bye
EOF
  echo '_tmp/bad.html' | htm8-tool well-formed 
}

# site errors
#
# Error in 'release/0.7.pre5/doc/osh-quick-ref.html': (LexError '&& or ||</h4>\n<!-- 2')
# Error in 'src/data/symbol.html': (LexError "&& mangle[0]!='E' &&")
# 5833374 tokens in 4710 files
#
# The second is the "Woboq" browser, which has CDATA
# Ah I wonder if we need that.

# Takes ~13 seconds
test-site() {
  local new_site=${1:-}

  # TODO: 
  # - test that the top level lexes
  #   - test that each tag lexers
  #     - test that each quoted attribute lexes
  # - test that tags are balanced

  if test -n "$new_site"; then
    dir='../oils.pub__deploy'
  else
    dir='../../oilshell/oilshell.org__deploy'
  fi

  pushd $dir

  # Too many files
  # site-files | xargs wc -l | grep total

  # Not using xargs
  time site-files | $REPO_ROOT/$0 htm8-tool validate

  popd
}

readonly SOIL_ID=8917
readonly WWZ_DIR=_tmp/$SOIL_ID

sync-wwz() {
  mkdir -p $WWZ_DIR
  rsync --archive --verbose \
    op.oilshell.org:op.oilshell.org/uuu/github-jobs/$SOIL_ID/ $WWZ_DIR/
}

extract-wwz() {
  pushd $WWZ_DIR
  for z in *.wwz; do
    local name=$(basename $z .wwz)

    mkdir -p $name
    pushd $name >/dev/null

    echo $name
    unzip ../$z

    popd >/dev/null
  done
  popd
}

tree-wwz() {
  tree $WWZ_DIR
}

test-wwz() {
  pushd $WWZ_DIR

  time find . -name '*.html' | $REPO_ROOT/$0 htm8-tool validate

  popd
}

find-xml() {
  time find ~ -iname '*.xml' | tee _tmp/xml-files.txt
}

test-other-xml() {
  # problem with &ent1;
  # CDATA support!  haha OK
  time cat _tmp/xml-files.txt | $REPO_ROOT/$0 htm8-tool validate
}

test-repo-xml() {
  # OK these parse
  time find . -name '_chroot' -a -prune -o -name '*.xml' -a -print \
    | $REPO_ROOT/$0 htm8-tool validate
}

test-repo-html() {
  time find . -name '*.html' | $REPO_ROOT/$0 htm8-tool validate
}

test-docs() {
  time find _release/VERSION -name '*.html' | $REPO_ROOT/$0 htm8-tool validate
}

soil-run() {
  test-docs
}

# OK we have to skip the <script> tag!  And <style>
#
# document.location = '#' + params.join('&');
# gUrlHash = new UrlHash(location.hash);
#
# I think textarea we don't though?


task-five "$@"
exit


echo '
In HTML5, instead of
<script>
<![CDATA[
  if (x < y) { ... }
]]>
</script>

You can write

<script>
 if (x < y) { ... }
</script>

<script> <style> <textarea>

These have special escaping rules.  I guess we just do NOT lex them at all?
We can totally SKIP them.

CDATA vs. RCDATA

<textarea>
  &lt;p&gt;  <!-- This will show as: <p> -->
  &amp;    <!-- This will show as: & -->
</textarea>

<script>
  &lt;p&gt;  <!-- This will show literally as: &lt;p&gt; -->
  &amp;     <!-- This will show literally as: &amp; -->
</script>

The main practical difference is that RCDATA processes HTML entities while
CDATA treats them as literal text. Both modes ignore HTML tags (treating them
as plain text) except for their own closing tag.  '
'

