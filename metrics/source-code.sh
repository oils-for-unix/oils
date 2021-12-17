#!/usr/bin/env bash
#
# Count lines of code in various ways.
#
# Usage:
#   metrics/source-code.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

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

  ls bin/oil.py {osh,core,frontend,qsn_}/*.py native/*.c */*.pyi "${ASDL_FILES[@]}" \
    | filter-py | grep -E -v 'posixmodule.c$|line_input.c$|_gen.py$|test_lib.py$|os.pyi$'
}

oil-lang-files() {
  ls oil_lang/*.{py,pgen2} tea/*.py | filter-py 
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
      if not line or line.startswith("--"):
        continue
      num_lines += 1

  print "%5d %s" % (num_lines, path)
  total += num_lines

print "%5d %s" % (total, "total")
' "$@"
}

osh-cloc() {
  echo 'OSH (non-blank non-comment lines)'
  echo
  osh-files | xargs cloc --quiet "$@"

  # NOTE: --csv option could be parsed into HTML.
  # Or just sum with asdl-cloc!

  echo
  echo 'ASDL SCHEMAS (non-blank non-comment lines)'
  asdl-cloc "${ASDL_FILES[@]}"
}

#
# Variants
#

wc-text() {
  xargs wc -l "$@" | sort --numeric
}

wc-html() {
  # Create HTML
  xargs wc -l "$@" | metrics/wc_html.py
}

header-html() {
  echo "<h2>$1</h2>"
}

comment-html() {
  echo "<p>$1</p>"
}

html-head() {
  PYTHONPATH=. doctools/html_head.py "$@"
}

metrics-html-head() {
  local title="$1"

  local base_url='../../../web'

  html-head --title "$title" "$base_url/base.css" "$base_url/line-counts.css" 
}

#
# Helper functions
#

osh-counts() {
  local header=${1:-echo}
  local comment=${2:-true}
  local count=${3:-wc-text}

  $header 'OSH (and common libraries)'
  $comment 'This is the input to the translator, written in statically-typed Python.'
  osh-files | $count
  echo
}

cpp-counts() {
  local header=${1:-echo}
  local comment=${2:-true}
  local count=${3:-wc-text}

  $header 'Hand-written C++ Code, like OS bindings'
  $comment 'The small C++ files correspond to larger Python files, like osh/arith_parse.py.'

  ls cpp/*.{cc,h} | egrep -v 'greatest.h|unit_tests.cc' | $count
  echo

  $header 'Old mycpp Runtime (no garbage collection)'
  ls mycpp/mylib.{cc,h} | $count
  echo

  $header 'New Garbage-Collected Runtime'
  ls mycpp/gc_heap.* mycpp/mylib2.* mycpp/my_runtime.* | $count
  echo

  $header 'Unit tests in C++'
  ls mycpp/*_test.cc cpp/unit_tests.cc | $count
  echo
}

gen-cpp-counts() {
  local header=${1:-echo}
  local comment=${2:-true}
  local count=${3:-wc-text}

  # NOTE: this excludes .re2c.h file
  $header 'Generated C+ Code'
  $comment 'This code is produced by many translators, including mycpp.
            Other translators are Zephyr ASDL and re2c.'
  ls _build/cpp/*.{cc,h} _devbuild/gen/*.h | $count
  echo
}

mycpp-counts() {
  local header=${1:-echo}
  local comment=${2:-true}
  local count=${3:-wc-text}

  $header 'mycpp translator'
  $comment 'This is a prototype (a hack on top of the MyPy frontend).'
  ls mycpp/*.py | grep -v 'build_graph.py' | filter-py | $count
  echo

  $header 'mycpp testdata'
  ls mycpp/examples/*.py | $count
  echo
}

#
# Top Level Summaries
#

for-translation() {
  local header=${1:-echo}
  local comment=${2:-true}
  local count=${3:-wc-text}

  mycpp-counts "$@"

  cpp-counts "$@"

  osh-counts "$@"

  gen-cpp-counts "$@"
}

all() {
  local header=${1:-echo}
  local comment=${2:-true}
  local count=${3:-wc-text}

  osh-counts "$@"

  $header 'Oil Language (and Tea)'
  oil-lang-files | $count
  echo

  $header 'BORROWED FROM STDLIB'
  ls pylib/*.py | filter-py | $count
  echo

  $header 'QSN library'
  ls qsn_/*.py | filter-py | $count
  echo

  $header 'SPEC TESTS'
  ls spec/*.test.sh | $count
  echo

  $header 'OIL UNIT TESTS'
  ls {osh,frontend,core,native,tools}/*_test.py | $count
  echo

  $header 'OTHER UNIT TESTS'
  ls {build,test,asdl,pylib,tools}/*_test.py | $count
  echo

  $header 'GOLD TESTS'
  ls test/gold/*.sh | $count
  echo

  mycpp-counts "$@"

  # Leaving off cpp-counts since that requires a C++ build

  $header 'BUILD AUTOMATION'
  ls build/*.{mk,sh,py} Makefile *.mk configure install |
    filter-py | $count
  echo

  $header 'TEST AUTOMATION'
  ls test/*.{sh,py,R} | filter-py | grep -v jsontemplate.py |
    $count
  echo

  $header 'RELEASE AUTOMATION'
  ls devtools/release*.sh | $count
  echo

  $header 'SOIL (multi-cloud continuous build with containers)'
  ls soil/*.{sh,py} | $count
  echo

  $header 'BENCHMARKS'
  ls benchmarks/*.{sh,py,R} | $count
  echo

  $header 'METRICS'
  ls metrics/*.{sh,R} | $count
  echo

  $header 'ASDL'
  ls asdl/*.py | filter-py | grep -v -E 'arith_|tdop|_demo' |
    $count
  echo

  $header 'PGEN2 (parser generator)'
  ls pgen2/*.py | filter-py | $count
  echo

  $header 'OTHER CODE GENERATORS'
  ls */*_gen.py | $count
  echo

  $header 'GENERATED CODE (for app bundle)'
  ls _devbuild/gen/*.{py,h} | $count
  echo

  $header 'TOOLS'
  ls tools/*.py | filter-py | $count
  echo

  $header 'DOC TOOLS'
  ls {doctools,lazylex}/*.py | filter-py | $count
  echo

  $header 'WEB'
  ls web/*.js web/*/*.{js,py} | $count
  echo
}

#
# HTML Versions
#

for-translation-html() {
  local title='Code Overview: Translating Oil to C++'

  metrics-html-head "$title"
  echo '  <body class="width40">'

  echo "<h1>$title</h1>"

  for-translation header-html comment-html wc-html

  echo '  </body>'
  echo '</html>'
}

all-html() {
  local title='Code Overview'

  metrics-html-head "$title"
  echo '  <body class="width40">'

  echo "<h1>$title</h1>"

  all header-html comment-html wc-html

  echo '  </body>'
  echo '</html>'
}

write-reports() {
  # TODO:
  # - Put these in the right directory.
  # - Link from release page

  local dir=_tmp/metrics/line-counts

  mkdir -v -p $dir

  for-translation-html > $dir/for-translation.html
  all-html > $dir/all.html

  cat >$dir/index.html <<EOF
<a href="for-translation.html">for-translation</a> <br/>
<a href="all.html">all</a> <br/>
EOF

  ls -l $dir/*.html
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

opy-python-symbols() {
  local out_dir=${1:-_tmp/opy-test}
  _python-symbols bin/opy_.py opy $out_dir
}

old-style-classes() {
  oil-python-symbols | grep -v '<'
}

# Some of these are "abstract classes" like ChildStateChange
NotImplementedError() {
  grep NotImplementedError */*.py
}

if test $(basename $0) = 'source-code.sh'; then
  "$@"
fi
