#!/bin/bash
#
# Usage:
#   ./compile.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/common.sh

# TODO:
# - Can probably delete frozen*.c.  It might be more efficient in theory, but
# it's not the bottleneck.  It's less debuggable uses the fairly complex
# Tools/freeze.py and modulefinder module.  Have to remove hooks in import.c.
# - getpath.c can be removed.  Has hooks in sys.exec_prefix, etc. which we
# don't need.

readonly OVM_PYTHON_OBJS='
Python/_warnings.c
Python/bltinmodule.c
Python/ceval.c
Python/codecs.c
Python/errors.c
Python/frozen.c
Python/frozenmain.c
Python/future.c
Python/getargs.c
Python/getcompiler.c
Python/getcopyright.c
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
Python/pymath.c
Python/pystate.c
Python/pythonrun.c
Python/random.c
Python/structmember.c
Python/sysmodule.c
Python/traceback.c
Python/getopt.c
Python/pystrcmp.c
Python/pystrtod.c
Python/dtoa.c
Python/formatter_unicode.c
Python/formatter_string.c
'

OBJECT_OBJS='
Objects/abstract.c
Objects/boolobject.c
Objects/bufferobject.c
Objects/bytes_methods.c
Objects/bytearrayobject.c
Objects/capsule.c
Objects/cellobject.c
Objects/classobject.c
Objects/cobject.c
Objects/codeobject.c
Objects/complexobject.c
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
Objects/memoryobject.c
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
Objects/unicodeobject.c
Objects/unicodectype.c
'

# Non-standard lib stuff.
MODULE_OBJS='
Modules/getpath.c
Modules/main.c
Modules/gcmodule.c
'

# The stuff in Modules/Setup.dist, plus zlibmodule.c and signalmodule.c.
# NOTE: In Pyhon, signalmodule.c is specified in Modules/Setup.config, which
# comes from 'configure' output.
MODOBJS='
Modules/posixmodule.c
Modules/errnomodule.c  
Modules/pwdmodule.c
Modules/_sre.c  
Modules/_codecsmodule.c  
Modules/_weakref.c
Modules/zipimport.c  
Modules/signalmodule.c
'

OVM_LIBRARY_OBJS="
Modules/getbuildinfo.c
$OBJECT_OBJS
$OVM_PYTHON_OBJS 
$MODULE_OBJS
$MODOBJS
"

# Install prefix for architecture-independent files
readonly prefix='"/usr/local"'  # must be quoted string

# Install prefix for architecture-dependent files
readonly exec_prefix="$prefix"
readonly VERSION='"2.7"'
readonly VPATH='""'
readonly pythonpath='""'

# TODO:
# -D OVM_DISABLE_DLOPEN

readonly PREPROC_FLAGS=(
  -D OVM_MAIN \
  -D PYTHONPATH="$pythonpath" \
  -D PREFIX="$prefix" \
  -D EXEC_PREFIX="$exec_prefix" \
  -D VERSION="$VERSION" \
  -D VPATH="$VPATH" \
  -D Py_BUILD_CORE
)

readonly INCLUDE_PATHS=(-I . -I Include)
readonly CC=${CC:-cc}  # cc should be on POSIX systems

build() {
  local out=${1:-$PY27/ovm2}
  local module_init=${2:-$PY27/Modules/config.c}
  local main_name=${3:-_tmp/hello/main_name.c}
  local c_module_srcs=${4:-_tmp/hello/c-module-srcs-to-compile.txt}
  shift 4

  local abs_out=$PWD/$out
  local abs_module_init=$PWD/$module_init
  local abs_main_name=$PWD/$main_name
  local abs_c_module_srcs=$PWD/$c_module_srcs

  #echo $OVM_LIBRARY_OBJS

  # HAVE_READLINE defined in detected-config.sh.
  source-detected-config-or-die

  pushd $PY27

  local compile_readline
  local link_readline
  if test "$HAVE_READLINE" = 1; then
    # Readline interface for tokenizer.c and [raw_]input() in bltinmodule.c.
    # For now, we are using raw_input() for the REPL.  TODO: Parameterize this!
    # We should create a special no_readline_raw_input().
    compile_readline='-D HAVELIB_READLINE Parser/myreadline.c'
    link_readline='-l readline'
  else
    compile_readline=''
    link_readline=''
  fi

  # Slower when done serially.
  # PREFIX, EXEC_PREFIX, VERSION, VPATH, etc. are from Modules/getpath.o

  # So the OVM is ~600K smaller now.  1.97 MB for ./run.sh build-default.  1.65
  # MB for ./run.sh build-clang-small.
  time $CC \
    "${INCLUDE_PATHS[@]}" \
    "${PREPROC_FLAGS[@]}" \
    -o $abs_out \
    $OVM_LIBRARY_OBJS \
    $abs_module_init \
    $abs_main_name \
    $(cat $abs_c_module_srcs) \
    Modules/ovm.c \
    $compile_readline \
    -l m \
    $link_readline \
    "$@" \
    || true
  popd

  # NOTE:
  # -l readline -l termcap -- for Python readline.  Hm it builds without -l
  # termcap.
  # -l z , for zlibmodule.c, for zipimport
  # I think zlib is a statically linked dependency only, but it's still better
  # not to have it.
}

# build the optimized one.  Makefile uses -O3.

# Clang -O2 is 1.37 MB.  18 seconds to compile.
#   -m32 is 1.12 MB.  But I probably have to redefine a few things because
#   there are more warnings.
# -O3 is 1.40 MB.

# GCC -O2 is 1.35 MB.  21 seconds to compile.

build-dbg() {
  build "$@" -O0 -g
}

# http://stackoverflow.com/questions/1349166/what-is-the-difference-between-gcc-s-and-a-strip-command
# Generate a stripped binary rather than running strip separately.
build-opt() {
  build "$@" -O3 -s
}

#
# Source Release (uses same files
#

add-py27() {
  xargs -I {} -- echo $PY27/{}
}

python-sources() {
  echo "$OVM_LIBRARY_OBJS" | add-py27
}

_headers() {
  local c_module_srcs=${1:-_tmp/hello/c-module-srcs.txt}
  local abs_c_module_srcs=$PWD/$c_module_srcs

  # -MM: no system headers
  cd $PY27
  gcc \
    "${INCLUDE_PATHS[@]}" \
    "${PREPROC_FLAGS[@]}" \
    -MM $OVM_LIBRARY_OBJS \
    Modules/ovm.c \
    $(cat $abs_c_module_srcs) 
}

# NOTE: 91 headers in Include, but only 81 referenced here.  So it's worth it.
# These are probably for the parser.
#
# NOTE: We also should get rid of asdl.h and so forth.

python-headers() {
  local c_module_srcs=$1
  # remove Python/.. -- it causes problems with tar.
  _headers $c_module_srcs | egrep --only-matching '[^ ]+\.h' \
    | sed 's|^Python/../||' \
    | sort | uniq | add-py27
}

make-tar() {
  local app_name=${1:-hello}
  local out=${2:-_release/hello.tar}

  # compile.sh is for the command line
  # actions.sh for concatenation
  #
  # NOTE: Need intermediate c-module-srcs.txt file so we can use the same
  # Makefile?  But if we didn't we might not need it?  It's really part of the
  # command line.

  local c_module_srcs=_build/$app_name/c-module-srcs.txt

  tar --create --file $out \
    LICENSE \
    INSTALL \
    Makefile \
    build/compile.sh \
    build/actions.sh \
    build/common.sh \
    _build/$app_name/bytecode.zip \
    _build/$app_name/*.c \
    $PY27/Modules/ovm.c \
    $c_module_srcs \
    $(cat $c_module_srcs | add-py27) \
    $(python-headers $c_module_srcs) \
    $(python-sources)

  # TODO: Add Python license at top level!

  ls -l $out
}

# 123K lines.
# Excluding MODOBJS, it's 104K lines.
#
# Biggest: posixmodule,unicodeobject,typeobject,ceval.
#
# Remove tmpnam from posixmodule, other cruft.
#
# Big ones to rid of: unicodeobject.c, import.c
# codecs and codecsmodule?  There is some non-unicode stuff there though.
#
# Probably need unicode for compatibility with modules and web frameworks
# especially.

count-c-lines() {
  pushd $PY27
  wc -l $OVM_LIBRARY_OBJS | sort -n

  # 90 files.
  # NOTE: To count headers, use the tar file.
  echo
  echo 'Files:'
  { for i in $OVM_LIBRARY_OBJS; do
     echo $i
    done
  } | wc -l

  popd
}

"$@"
