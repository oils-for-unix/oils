#!/usr/bin/env bash
#
# Count lines of code in various ways.
#
# Usage:
#   metrics/source-code.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd $(dirname $0)/.. && pwd)  # tsv-lib.sh uses this
readonly REPO_ROOT

source test/common.sh
source test/tsv-lib.sh

filter-py() {
  grep -E -v '__init__.py$|_gen.py|_test.py|_tests.py$'
}

readonly -a ASDL_FILES=( {frontend,core}/*.asdl )

# OSH and common
osh-files() {
  # Exclude:
  # - line_input.c because I didn't write it.  It still should be minimized.
  # - code generators
  # - test library

  ls bin/oils_for_unix.py {osh,core,frontend}/*.py pyext/*.c */*.pyi \
    "${ASDL_FILES[@]}" \
    | filter-py | grep -E -v 'posixmodule.c$|line_input.c$|_gen.py$|test_lib.py$|os.pyi$'
}

ysh-files() {
  ls ysh/*.{py,pgen2} {data_lang,library}/*.py | filter-py 
}

# cloc doesn't understand ASDL files.
# Use a wc-like format, filtering out blank lines and comments.
asdl-cloc() {
  python -c '
import sys

total = 0
for path in sys.argv[1:]:
  num_lines = 0
  with open(path) as f:
    for line in f:
      line = line.strip()
      if not line or line.startswith("#"):
        continue
      num_lines += 1

  print "%5d %s" % (num_lines, path)
  total += num_lines

print "%5d %s" % (total, "total")
' "$@"
}

cloc-report() {
  echo 'OSH (non-blank non-comment lines)'
  echo
  osh-files | xargs cloc --quiet "$@"
  echo
  echo

  echo 'YSH (non-blank non-comment lines)'
  echo
  ysh-files | xargs cloc --quiet "$@"

  # NOTE: --csv option could be parsed into HTML.
  # Or just sum with asdl-cloc!

  echo
  echo 'ASDL SCHEMAS (non-blank non-comment lines)'
  asdl-cloc "${ASDL_FILES[@]}"
}

preprocessed() {
  ./NINJA-config.sh

  # Clang has slightly fewer lines, but it's not on the CI machine
  #local -a files=(_build/preprocessed/{cxx,clang}-{dbg,opt}.txt)

  local -a files=(_build/preprocessed/cxx-{dbg,opt}.txt)

  ninja "${files[@]}"

  # Publish with release and show and CI

  local dir=_tmp/metrics/preprocessed
  mkdir -p $dir
  cp -v "${files[@]}" $dir

  cat >$dir/index.html <<EOF
<a href="cxx-dbg.txt">cxx-dbg.txt</a> <br/>
<a href="cxx-opt.txt">cxx-opt.txt</a> <br/>
EOF

  head -n 100 $dir/*.txt
}

#
# Two variants of the $count function: text and html
#

category-text() {
  local header=$1
  local comment=$2

  echo "$header"
  # omit comment

  # stdin is the files
  xargs wc -l | sort --numeric
  echo
}

# This is overly clever ...
shopt -s lastpipe
SECTION_ID=0  # mutable global

category-html() {
  # TODO: Don't use wc -l, and just count and sum the lines yourself

  xargs wc -l | metrics/line_counts.py $((++SECTION_ID)) "$@"
}

#
# Functions That Count
#

# Note this style is OVERLY ABSTRACT, but it's hard to do better in shell.  We
# want to parameterize over text and HTML.  In Oil I think we would use this:
#
# proc p1 {
#   category 'OSH (and common libraries)' {
#     comment = 'This is the input'
#     osh-files | read --lines :files
#   }
# }
#
# This produces a series of dicts that looks like
# { name: 'OSH ...', comment: "This ...", files: %(one two three) }
#
# Then we iterate over the categories and produce text or HTML.

osh-counts() {
  local count=$1
  shift

  osh-files | $count \
    'OSH (and common libraries)' \
    'This is the input to the translators, written in statically-typed Python.  Note that bash is at least 140K lines of code, and OSH implements a large part of bash and more.' \
    "$@"
}

ysh-counts() {
  local count=$1
  shift

  ysh-files | $count \
    'YSH' 'Expression grammar, parser, evaluator, etc.' "$@"
}

cpp-counts() {
  local count=$1
  shift

  ls cpp/*.{cc,h} | egrep -v 'greatest.h|_test.cc' | $count \
    'Hand-written C++ Code' \
    'Includes OS bindings.  Small C++ files like cpp/osh_arith_parse.{cc,h} correspond to larger Python files like osh/arith_parse.py.' \
    "$@"

  # Remove code that isn't "in production"
  ls mycpp/*.{cc,h} | egrep -v '_test.cc|bump_leak_heap' \
    | $count \
    'Garbage-Collected Runtime' \
    'Uses a fork-friendly Mark-Sweep collector.' \
    "$@"

  ls mycpp/*_test.cc cpp/*_test.cc | $count \
    'Unit tests in C++' \
    'The goal is to make the spec tests pass, but unit tests are helpful too.' \
    "$@"

  ls NINJA*.sh */NINJA*.py build/ninja*.{sh,py} | $count \
    'Incremental C++ Build' '' "$@"
}

gen-cpp-counts() {
  local count=$1
  shift

  # NOTE: this excludes .re2c.h file
  ls _gen/*/*.{cc,h} | $count \
    'Generated C++ Code' \
    'mycpp generates the big file _gen/bin/oils-for-unix.mycpp.cc.  Other programs like Zephyr ASDL and re2c generate other files.' \
    "$@"
}

mycpp-counts() {
  local count=$1
  shift

  ls mycpp/*.py | grep -v 'NINJA_subgraph.py' | filter-py | $count \
    'mycpp Translator' \
    "This prototype uses the MyPy frontend to translate statically-typed Python to C++.  The generated code calls a small runtime which implements things like List[T], Dict[K, V], and Python's len()." \
    "$@"

  ls mycpp/examples/*.py | $count \
    'mycpp Test Data' \
    'Small Python examples that translate to C++, compile, and run.' \
    "$@"
}

code-generator-counts() {
  local count=$1
  shift

  ls asdl/*.py | filter-py | grep -v -E 'arith_|tdop|_demo' | $count \
    'Zephyr ASDL' \
    'A DSL for algebraic data types, borrowed from Python.  Oil is the most strongly typed Bourne shell implementation!' \
    "$@"

  ls pgen2/*.py | filter-py | $count \
    'pgen2 Parser Generator' \
    'An LL(1) parser generator used to parse Oil expressions.  Also borrowed from CPython.' \
    "$@"

  ls */*_gen.py | $count \
    'Other Code Generators' \
    'In order to make Oil statically typed, we had to abandon Python reflection and use C++ source code generation instead.  The lexer, flag definitions, and constants can be easily compiled to C++.' \
    "$@"
}

spec-gold-counts() {
  local count=$1
  shift

  ls spec/*.test.sh | $count \
    'Spec Tests' \
    'A comprehensive test suite that compares OSH against other shells.  If OSH passes these tests in BOTH Python and C++, it means that the translation works.' \
    "$@"

  ls test/gold/*.sh | $count \
    'Gold Tests' \
    'Another suite that tests shells "from the outside".  Instead of making explicit assertions, we verify that OSH behaves like bash.' \
    "$@"
}

#
# Top Level Summaries
#

_for-translation() {
  local count=$1
  shift

  mycpp-counts $count "$@"

  code-generator-counts $count "$@"

  cpp-counts $count "$@"

  osh-counts $count "$@"

  ysh-counts $count "$@"

  spec-gold-counts $count "$@"

  gen-cpp-counts $count "$@"
}

_overview() {
  local count=$1
  shift

  osh-counts $count "$@"

  ysh-counts $count "$@"

  ls stdlib/*.ysh | $count \
    "YSH stdlib" '' "$@"

  ls pylib/*.py | filter-py | $count \
    "Code Borrowed from Python's stdlib" '' "$@"

  spec-gold-counts $count "$@"

  test/unit.sh py2-tests | $count \
    'Python Unit Tests' '' "$@"

  ls test/*.{sh,py,R} | filter-py | grep -v jsontemplate.py | $count \
    'Other Shell Tests' '' "$@"

  ls */TEST.sh | $count \
    'Test Automation' '' "$@"

  mycpp-counts $count "$@"

  code-generator-counts $count "$@"

  cpp-counts $count "$@"

  # Leaving off gen-cpp-counts since that requires a C++ build

  ls build/*.{mk,sh,py,c} Makefile configure install \
    | filter-py | egrep -v 'NINJA|TEST' | $count \
    'Build Automation' '' "$@"

  ls devtools/release*.sh | $count \
    'Release Automation' '' "$@"

  ls soil/*.{sh,py} | $count \
    'Soil: Multi-cloud CI with containers' '' "$@"

  ls benchmarks/*.{sh,py,R} | $count \
    'Benchmarks' '' "$@"

  ls metrics/*.{sh,R} | $count \
    'Metrics' '' "$@"

  ls _devbuild/gen/*.py | $count \
    'Generated Python Code' \
    'For the Python App Bundle.' \
    "$@"

  ls tools/*.py | filter-py | $count \
    'Tools' '' "$@"

  ls {doctools,lazylex}/*.py doctools/*.{h,cc} | filter-py | $count \
    'Doc Tools' '' "$@"

  ls web/*.js web/*/*.{js,py} | $count \
    'Web' '' "$@"
}

for-translation() {
  _for-translation category-text
}

overview() {
  _overview category-text
}

print-files() {
  xargs -n 1 -- echo
}

overview-list() {
  _overview print-files
}

#
# HTML Versions
#

html-head() {
  PYTHONPATH=. doctools/html_head.py "$@"
}

metrics-html-head() {
  local title="$1"

  local base_url='../../../web'

  html-head --title "$title" "$base_url/base.css" "$base_url/table/table-sort.css" "$base_url/line-counts.css" 
}

counts-html() {
  local name=$1
  local title=$2

  local tmp_dir=_tmp/metrics/line-counts/$name

  rm -r -f -v $tmp_dir >& 2
  mkdir -v -p $tmp_dir >& 2

  tsv-row category category_HREF total_lines num_files > $tmp_dir/INDEX.tsv

  echo $'column_name\ttype
category\tstring
category_HREF\tstring
total_lines\tinteger
num_files\tinteger' >$tmp_dir/INDEX.schema.tsv 

  # Generate the HTML
  "_$name" category-html $tmp_dir

  metrics-html-head "$title"
  echo '  <body class="width40">'

  echo "<h1>$title</h1>"

  tsv2html $tmp_dir/INDEX.tsv

  echo '<hr/>'

  echo '<h2>Related Documents</h2>
        <p>The <a href="https://www.oilshell.org/release/latest/doc/README.html">README for oilshell/oil</a>
           has another overview of the repository.
        </p>'

  # All the parts
  cat $tmp_dir/*.html

  echo '  </body>'
  echo '</html>'
}

for-translation-html() {
  local title='Overview: Translating Oil to C++'
  counts-html for-translation "$title"
}

overview-html() {
  local title='Overview of Oil Code'
  counts-html overview "$title"
}

write-reports() {
  local out_dir=${1:-_tmp/metrics/line-counts}

  mkdir -v -p $out_dir

  for-translation-html > $out_dir/for-translation.html

  overview-html > $out_dir/overview.html

  cat >$out_dir/index.html <<EOF
<a href="for-translation.html">for-translation</a> <br/>
<a href="overview.html">overview</a> <br/>
EOF

  ls -l $out_dir
}

#
# Misc
#

# count instructions, for fun
instructions() {
  # http://pepijndevos.nl/2016/08/24/x86-instruction-distribution.html

  local bin=_build/oil/ovm-opt.stripped
  objdump -d $bin | cut -f3 | grep -oE "^[a-z]+" | hist
}

hist() {
  sort | uniq -c | sort -n
}

stdlib-imports() {
  oil-osh-files | xargs grep --no-filename '^import' | hist
}

imports() {
  oil-osh-files | xargs grep --no-filename -w import | hist
}

imports-not-at-top() {
  oil-osh-files | xargs grep -n -w import | awk -F : ' $2 > 100'
}

# For the compiler, see what's at the top level.
top-level() {
  grep '^[a-zA-Z]' {core,osh}/*.py \
    | grep -v '_test.py'  \
    | egrep -v ':import|from|class|def'  # note: colon is from grep output
}

_python-symbols() {
  local main=$1
  local name=$2
  local out_dir=$3

  mkdir -p $out_dir
  local out=${out_dir}/${name}-symbols.txt

  # To debug what version we're running eci
  /usr/bin/env python2 -V
  echo

  # Run this from the repository root.
  PYTHONPATH='.:vendor/' CALLGRAPH=1 $main | tee $out

  wc -l $out
  echo 
  echo "Wrote $out"
}

oil-python-symbols() {
  local out_dir=${1:-_tmp/opy-test}
  _python-symbols bin/oil.py oil $out_dir
}

old-style-classes() {
  oil-python-symbols | grep -v '<'
}

# Some of these are "abstract classes" like ChildStateChange
NotImplementedError() {
  grep NotImplementedError */*.py
}

py-ext() {
  # for the py-source build
  # 35 imports
  osh-files | xargs -- egrep 'import (fanos|libc|line_input|posix_|yajl)'
}

if test $(basename $0) = 'source-code.sh'; then
  "$@"
fi
