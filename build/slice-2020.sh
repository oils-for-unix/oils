#!/bin/bash
#
# Usage:
#   ./slice-2020.sh <function name>

CFLAGS='-O0'  # for speed

source build/compile.sh

set -o nounset
set -o pipefail
set -o errexit


_OVM_PYTHON_OBJS='
Python/_warnings.c
Python/bltinmodule.c
Python/ceval.c
Python/errors.c
Python/getargs.c
Python/getcompiler.c
Python/getplatform.c
Python/getversion.c
Python/import.c
Python/marshal.c
Python/modsupport.c
Python/mystrtoul.c
Python/mysnprintf.c
Python/pyarena.c
Python/pyctype.c
Python/pyfpe.c
Python/pystate.c
Python/pythonrun.c
Python/random.c
Python/structmember.c
Python/sysmodule.c
Python/traceback.c
Python/pystrtod.c
Python/dtoa.c
Python/pymath.c
'
# NOTE: pystrtod.c needs some floating point functions in pymath.c

_OBJECT_OBJS='
Objects/abstract.c
Objects/boolobject.c
Objects/bufferobject.c
Objects/bytes_methods.c
Objects/capsule.c
Objects/cellobject.c
Objects/classobject.c
Objects/cobject.c
Objects/codeobject.c
Objects/descrobject.c
Objects/enumobject.c
Objects/exceptions.c
Objects/genobject.c
Objects/fileobject.c
Objects/floatobject.c
Objects/frameobject.c
Objects/funcobject.c
Objects/intobject.c
Objects/iterobject.c
Objects/listobject.c
Objects/longobject.c
Objects/dictobject.c
Objects/methodobject.c
Objects/moduleobject.c
Objects/object.c
Objects/obmalloc.c
Objects/rangeobject.c
Objects/setobject.c
Objects/sliceobject.c
Objects/stringobject.c
Objects/structseq.c
Objects/tupleobject.c
Objects/typeobject.c
Objects/weakrefobject.c
'

# Non-standard lib stuff.
_MODULE_OBJS='
Modules/gcmodule.c
'

# The stuff in Modules/Setup.dist, signalmodule.c.  NOTE: In Python,
# signalmodule.c is specified in Modules/Setup.config, which comes from
# 'configure' output.
_MODOBJS='
Modules/errnomodule.c
Modules/_weakref.c
Modules/zipimport.c
Modules/signalmodule.c
'

# Parser/myreadline.c is needed for raw_input() to work.  There is a dependency
# from Python/bltinmodule.c to it.
_OVM_LIBRARY_OBJS="
Modules/getbuildinfo.c
Parser/myreadline.c
$_OBJECT_OBJS
$_OVM_PYTHON_OBJS
$_MODULE_OBJS
$_MODOBJS
"

demo() {
  local abs_out=$PWD/_tmp/demo
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
    -D PREFIX="\"$PREFIX\"" \
    -D EXEC_PREFIX="\"$PREFIX\"" \
    -o $abs_out \
    $_OVM_LIBRARY_OBJS \
    $main \
    -l m \
    ${BASE_LDFLAGS} \
    ${LDFLAGS} \
    "$@" || true
}

# 35K lines of .c files, and 40K lines with headers
# of course we have some other dependencies like math and string libs.
source-files() {
  egrep -v 'class|frame|set' <<EOF
Objects/boolobject.c
Objects/cellobject.c
Objects/classobject.c
Objects/cobject.c
Objects/enumobject.c
Objects/genobject.c
Objects/fileobject.c
Objects/floatobject.c
Objects/frameobject.c
Objects/funcobject.c
Objects/iterobject.c
Objects/listobject.c
Objects/longobject.c
Objects/dictobject.c
Objects/methodobject.c
Objects/moduleobject.c
Objects/object.c
Objects/rangeobject.c
Objects/setobject.c
Objects/sliceobject.c
Objects/stringobject.c
Objects/tupleobject.c
Objects/typeobject.c
EOF
  #return

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
