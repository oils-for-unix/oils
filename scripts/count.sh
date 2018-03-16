#!/usr/bin/env bash
#
# Count lines of code in various ways.
#
# Usage:
#   ./count.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

filter-py() {
  grep -E -v '__init__.py$|_test.py$'
}

# Oil-only would exclude core/legacy.py, etc.
oil-osh-files() {
  { ls {bin,osh,core}/*.py native/*.c osh/{osh,types}.asdl core/runtime.asdl; } |
    filter-py | grep -E -v '_gen.py$|test_lib.py'
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

oil-osh-cloc() {
  echo 'OIL AND OSH (non-blank non-comment lines)'
  echo
  oil-osh-files | xargs cloc --quiet "$@"

  # NOTE: --csv option could be parsed into HTML.
  # Or just sum with asdl-cloc!

  echo
  echo 'ASDL SCHEMAS (non-blank non-comment lines)'
  asdl-cloc osh/osh.asdl core/runtime.asdl
}

# TODO: Sum up all the support material.  It's more than Oil itself!  Turn
# everything into an array.  An hash table of arrays would be useful here.
all() {
  echo 'BUILD AUTOMATION'
  wc -l build/*.{mk,sh,py} Makefile *.mk configure install |
    filter-py | sort --numeric
  echo

  echo 'TEST AUTOMATION'
  wc -l test/*.{sh,py,R} | filter-py | sort --numeric
  echo

  echo 'RELEASE AUTOMATION'
  wc -l scripts/release.sh | sort --numeric
  echo

  echo 'BENCHMARKS'
  wc -l benchmarks/*.{sh,py,R} | sort --numeric
  echo

  echo 'SPEC TESTS'
  wc -l spec/*.test.sh | sort --numeric
  echo

  echo 'GOLD TESTS'
  wc -l gold/*.sh | sort --numeric
  echo

  echo 'ASDL'
  wc -l asdl/{asdl_*,const,py_meta,encode,format}.py | sort --numeric
  echo

  echo 'CODE GENERATORS'
  wc -l asdl/gen_*.py */*_gen.py | sort --numeric
  echo

  echo 'GENERATED CODE'
  wc -l _devbuild/gen/*.{py,h} | sort --numeric
  echo

  echo 'TOOLS'
  ls tools/*.py | filter-py | xargs wc -l | sort --numeric
  echo

  echo 'WEB'
  ls web/*.js web/*/*.{js,py} | xargs wc -l | sort --numeric
  echo

  echo 'OTHER UNIT TESTS'
  wc -l {build,test,asdl,tools}/*_test.py | sort --numeric
  echo

  echo 'OIL UNIT TESTS'
  wc -l {osh,core,native,tools}/*_test.py | sort --numeric
  echo

  echo 'OIL AND OSH'
  oil-osh-files |
    xargs wc -l | sort --numeric
  echo

  return
  # TODO: Import docs

  echo 'DOCS'
  wc -l README.md doc/* | sort --numeric
  echo
}

# Just the parser
parser() {
  echo 'AST and IDs'
  wc -l osh/osh.asdl core/id_kind.py | sort -n
  echo

  echo 'Lexer / Parser'
  wc -l osh/{*_parse.py,lex.py,parse_lib.py} core/word.py | sort -n
  echo

  echo 'Compiler / Middle End'
  wc -l core/{braces,word_compile}.py | sort -n
  echo

  echo 'Common Algorithms'
  wc -l core/{tdop,lexer}.py | sort -n
  echo

  echo 'Utilities'
  wc -l core/{alloc,ui,reader}.py | sort -n
  echo
}

# Stuff we might need to hand-port
parser-port() {
  wc -l core/tdop.py osh/*_parse.py | sort -n
}

runtime() {
  # NOTE: braces.py contains both parsing and runtime.  It is a  middle stage.

  echo 'Runtime'
  wc -l core/{process,state}.py core/runtime.asdl | sort -n
  echo

  # NOTE: These may turn into compilers
  echo 'Evaluators'
  wc -l core/*_{exec,eval}.py | sort -n
  echo

  echo 'Builtins'
  wc -l core/{builtin,test_builtin}.py
  echo

  echo 'Libraries'
  wc -l core/{args,glob_,legacy,libstr}.py | sort -n
  echo
}

# count instructions, for fun
instructions() {
  # http://pepijndevos.nl/2016/08/24/x86-instruction-distribution.html

  local bin=_tmp/oil
  objdump -d $bin | cut -f3 | grep -oE "^[a-z]+" | sort | uniq -c | sort -n
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

# For the compiler, see what's at the top level.
top-level() {
  grep '^[a-zA-Z]' {core,osh}/*.py \
    | grep -v '_test.py'  \
    | egrep -v ':import|from|class|def'  # note: colon is from grep output
}

_python-symbols() {
  local main=$1
  local name=$2

  local out=_tmp/${name}-python-symbols.txt

  CALLGRAPH=1 $main | tee $out

  wc -l $out
  echo 
  echo "Wrote $out"
}

oil-python-symbols() {
  _python-symbols bin/oil.py oil
}

opy-python-symbols() {
  _python-symbols bin/opy_.py opy
}

old-style-classes() {
  oil-python-symbols | grep -v '<'
}

"$@"
