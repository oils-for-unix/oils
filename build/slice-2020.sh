#!/bin/bash
#
# Usage:
#   ./slice-2020.sh <function name>

CFLAGS='-O0 -g'  # for speed and debugging

source build/compile.sh

set -o nounset
set -o pipefail
set -o errexit

# TODO: Get rid of intobject.c in favor of longobject.c.  But it's tied in to
# many objects.  Probably need test coverage to do it safely.

# Note: setobject.c makes dictobject.c compile more easily.  Are we supporting
# it in Oil?

_OVM_LIBRARY_OBJS="
Python/mysnprintf.c

Python/getargs.c
Python/modsupport.c
Python/errors.c

Objects/boolobject.c

Python/mystrtoul.c
Objects/intobject.c

Python/pystrtod.c
Python/dtoa.c
Python/pymath.c
Objects/floatobject.c

Python/pyctype.c
Objects/stringobject.c

Objects/longobject.c
Objects/tupleobject.c

Objects/sliceobject.c
Objects/listobject.c

Objects/dictobject.c
Objects/setobject.c
Objects/iterobject.c
Objects/typeobject.c

Objects/abstract.c
Objects/object.c
Objects/obmalloc.c

Objects/exceptions.c
Modules/gcmodule.c

Objects/capsule.c
Objects/weakrefobject.c
"
# causes more errors?
#Objects/classobject.c

build() {
  local abs_out=$PWD/_tmp/py_object_main
  local main=$PWD/demo/py_object_main.c

  # From ./configure
  #local PREFIX=/usr/local

  # HAVE_READLINE defined in detected-config.sh.
  source-detected-config-or-die


  pushd $PY27

  # Note: all this defines MAIN_NAME and so forth.
  #
  # We want to get rid of ALL modules I suppose.  Man that's a bunch of work.
  # We're going to ONLY use objects.
  #
  # $abs_module_init \
  # $abs_main_name \
  # $c_module_src_list \

  time $CC \
    ${BASE_CFLAGS} \
    ${CFLAGS} \
    "${INCLUDE_PATHS[@]}" \
    "${PREPROC_FLAGS[@]}" \
    -D OBJECTS_ONLY \
    -D PREFIX="\"$PREFIX\"" \
    -D EXEC_PREFIX="\"$PREFIX\"" \
    -o $abs_out \
    $_OVM_LIBRARY_OBJS \
    $main \
    -l m \
    ${BASE_LDFLAGS} \
    ${LDFLAGS} \
    "$@" || true

  ls -l $abs_out
}

# 35K lines of .c files, and 40K lines with headers
# of course we have some other dependencies like math and string libs.
source-files() {
  echo $_OVM_LIBRARY_OBJS

  # These are mostly small
  for f in Include/*object.h; do
    echo $f
  done
}

count() {
  pushd $PY27
  source-files | xargs wc -l | sort -n
}

"$@"
