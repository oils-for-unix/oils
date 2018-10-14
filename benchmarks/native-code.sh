#!/bin/bash
#
# Usage:
#   ./native-code.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh  # for $R_PATH

readonly BASE_DIR=_tmp/metrics/native-code

# Size profiler for binaries.
bloaty() {
  ~/git/other/bloaty/bloaty "$@"
}

pylibc-symbols() {
  symbols _devbuild/py-ext/x86_64/libc.so
}

fastlex-symbols() {
  symbols _devbuild/py-ext/x86_64/fastlex.so
}

symbols() {
  local obj=$1
  nm $obj
  echo

  bloaty $obj
  echo

  # fastlex_MatchToken is 21.2 KiB.  That doesn't seem to large compared ot
  # the 14K line output?
  bloaty -d symbols $obj
  echo

  ls -l $obj
  echo
}

# Big functions:
# - PyEval_EvalFrameEx (38 KiB)
# - fastlex_MatchOSHToken (22.5 KiB)
# - convertitem() in args.py (9.04 KiB)
# - PyString_Format() in args.py (6.84 KiB)
#
# Easy removals:
# - marshal_dumps and marshal_dump!  We never use those.
# - Remove all docstrings!!!  Like sys_doc.

cpython-compileunits() {
  # Hm there doesn't seem to be a way to do this without
  local file=_build/oil/ovm-dbg

  #local file=_build/oil/ovm-opt
  #local sym=_build/oil/ovm-opt.symbols

  bloaty --tsv -n 0 -d compileunits $file 
}

cpython-symbols() {
  # NOTE: This is different than the release binary!
  # ovm-opt.stripped doesn't show a report.
  local file=_build/oil/ovm-opt

  # Slightly different.
  #local file=_build/oil/ovm-dbg

  #bloaty -n 30 -d symbols $file

  # Full output
  # 3,588 lines!
  bloaty --tsv -n 0 -d symbols $file 
}

_report() {
  R_LIBS_USER=$R_PATH benchmarks/native-code.R "$@"
}

report() {
  _report metrics $BASE_DIR
}

build-ovm() {
  make _build/oil/ovm-{dbg,opt}
}

run-for-release() {
  build-ovm

  mkdir -p $BASE_DIR
  cpython-symbols > $BASE_DIR/symbols.tsv

  # Really 'transation units', but bloaty gives it that name.
  cpython-compileunits > $BASE_DIR/compileunits.tsv

  head $BASE_DIR/symbols.tsv $BASE_DIR/compileunits.tsv

  report
}

# TODO:
# Write to a separate file like _build/pydefs/intobject.include
# #ifdef OVM_MAIN
# #include "intobject.include"
# #else
# ...
# #end
#
# Should those files be checked in an edited by hand?  Or join them somehow
# with oil-symbols.txt?
# I think this is hard because of METHODS.
# Maybe you should have a config file that controls it.  It takes a .include
# file and then whitelist/blacklist, and then generates a new one.
# could put it in build/pydefs-config.txt
#
# And then reprint the PyMethoDef without docstrings?  It shouldn't be that
# hard to parse.  You can almost do it with a regex, since commas don't appear
# in the string.

extract-defs() {
  # NOTE: PyMemberDef is also interesting, but we don't need it for the build.
  gawk '
  /static PyMethodDef/ {
    if (printing != 0) {
      printf("%s:%d Expected not to be printing\n", FILENAME, FNR);
      exit 1;
    }
    printing = 1;
    printf("\n");
    printf("/* Extracted from %s */\n", FILENAME);
  }

  {
    if (printing) {
      print
    }
  }

  /^[:space:]*\}/ {
    printing = 0;
  }
  ' "$@"
}

source build/common.sh  # $PY27

# TODO: Use PREPROC_FLAGS from build/compile.sh.
preprocess() {
  # What about stuff in pyconfig.h?
  gcc -I $PY27 -E -D OVM_MAIN -
}

extract-all-defs() {
  echo '#include "pyconfig.h"'
  # 52 different instances.  Sometimes multiple ones per file.
  find _tmp/oil-tar-test -name '*.[ch]' | xargs -- $0 extract-defs 
}

py-method-defs() {
  extract-all-defs #| preprocess
}


"$@"
