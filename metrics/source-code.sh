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

mycpp-counts() {
  echo 'MYCPP translator'
  ls mycpp/*.py | grep -v 'build_graph.py' | filter-py | xargs wc -l | sort --numeric
  echo
}

# TODO: Sum up all the support material.  It's more than Oil itself!  Turn
# everything into an array.  An hash table of arrays would be useful here.
all() {

  echo 'BUILD AUTOMATION'
  ls build/*.{mk,sh,py} Makefile *.mk configure install |
    filter-py | xargs wc -l | sort --numeric
  echo

  echo 'TEST AUTOMATION'
  ls test/*.{sh,py,R} | filter-py | grep -v jsontemplate.py |
    xargs wc -l | sort --numeric
  echo

  echo 'RELEASE AUTOMATION'
  wc -l devtools/release*.sh | sort --numeric
  echo

  echo 'SOIL'
  wc -l soil/*.{sh,py} | sort --numeric
  echo

  echo 'BENCHMARKS'
  wc -l benchmarks/*.{sh,py,R} | sort --numeric
  echo

  echo 'METRICS'
  wc -l metrics/*.{sh,R} | sort --numeric
  echo

  echo 'SPEC TESTS'
  wc -l spec/*.test.sh | sort --numeric
  echo

  echo 'GOLD TESTS'
  wc -l test/gold/*.sh | sort --numeric
  echo

  echo 'ASDL'
  ls asdl/*.py | filter-py | grep -v -E 'arith_|tdop|_demo' |
    xargs wc -l | sort --numeric
  echo

  mycpp-counts

  echo 'PGEN2 (parser generator)'
  ls pgen2/*.py | filter-py | xargs wc -l | sort --numeric
  echo

  echo 'QSN'
  ls qsn_/*.py | filter-py | xargs wc -l | sort --numeric
  echo

  echo 'DOC TOOLS'
  ls {doctools,lazylex}/*.py | filter-py | xargs wc -l | sort --numeric
  echo

  # NOTE: OPy is counted separately.

  echo 'CODE GENERATORS'
  wc -l */*_gen.py | sort --numeric
  echo

  echo 'GENERATED CODE (for app bundle)'
  wc -l _devbuild/gen/*.{py,h} | sort --numeric
  echo

  echo 'TOOLS'
  ls tools/*.py | filter-py | xargs wc -l | sort --numeric
  echo

  echo 'WEB'
  ls web/*.js web/*/*.{js,py} | xargs wc -l | sort --numeric
  echo

  echo 'BORROWED FROM STDLIB'
  ls pylib/*.py | filter-py | xargs wc -l | sort --numeric
  echo

  echo 'OTHER UNIT TESTS'
  wc -l {build,test,asdl,pylib,tools}/*_test.py | sort --numeric
  echo

  echo 'OIL UNIT TESTS'
  wc -l {osh,frontend,core,native,tools}/*_test.py | sort --numeric
  echo

  osh-counts

  echo 'Oil Language (and Tea)'
  oil-lang-files | xargs wc -l | sort --numeric
  echo
}

osh-counts() {
  echo 'OSH (and common libraries)'
  osh-files | xargs wc -l | sort --numeric
  echo
}

cpp-counts() {
  echo 'Hand-Written C++ Code, like OS bindings'
  echo '(the small C++ files correspond to larger Python files, like osh/arith_parse.py)'
  ls cpp/*.{cc,h} | egrep -v 'greatest.h|unit_tests.cc' | xargs wc -l | sort --numeric
  echo

  echo 'Old mycpp Runtime (no garbage collection)'
  wc -l mycpp/mylib.{cc,h} | sort --numeric
  echo

  echo 'New Garbage-Collected Runtime'
  wc -l mycpp/gc_heap.* mycpp/mylib2.* mycpp/my_runtime.* | sort --numeric
  echo

  echo 'Unit tests in C++'
  wc -l mycpp/*_test.cc cpp/unit_tests.cc | sort --numeric
  echo

  # NOTE: this excludes .re2c.h file
  echo 'Generated C+ Code'
  echo '(produced by many translators including mycpp)'
  wc -l _build/cpp/*.{cc,h} _devbuild/gen/*.h | sort --numeric
  echo
}

for-compiler-engineer() {
  cpp-counts

  echo '# prototype of the translator: a hack on top of the MyPy frontend'
  mycpp-counts

  echo '# the input to the translator: statically-typed Python'
  osh-counts
}


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
