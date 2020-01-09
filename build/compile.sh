#!/usr/bin/env bash
#
# Usage:
#   ./compile.sh <function name>

set -o nounset
set -o pipefail
set -o errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

source build/common.sh

# NOTES on trying to delete certain modules:
#
# _warnings.c: There weren't that many; it probably could be deleted.
# bufferobject.c: the types.py module uses it.
# Python-ast.h: pythonrun.c uses it in several places (mod_ty), and a lot of
# stuff uses pythonrun.c.
# pythonrun.c: lots interpreter flags and interpreter initialization caused
# link errors.
# pyctype.c: Tables needed for many string operations.

# getargs.c: needed for Python-C API, e.g. PyArg_ParseTuple.
# dtoa.c: not tried, but I assume that %.3f for 'time' uses it.


readonly OVM_PYTHON_OBJS='
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

OBJECT_OBJS='
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
MODULE_OBJS='
Modules/main.c
Modules/gcmodule.c
'

# The stuff in Modules/Setup.dist, signalmodule.c.  NOTE: In Python,
# signalmodule.c is specified in Modules/Setup.config, which comes from
# 'configure' output.
MODOBJS='
Modules/errnomodule.c
Modules/pwdmodule.c
Modules/_weakref.c
Modules/zipimport.c
Modules/signalmodule.c
'

# Parser/myreadline.c is needed for raw_input() to work.  There is a dependency
# from Python/bltinmodule.c to it.
OVM_LIBRARY_OBJS="
Modules/getbuildinfo.c
Parser/myreadline.c
$OBJECT_OBJS
$OVM_PYTHON_OBJS
$MODULE_OBJS
$MODOBJS
"

readonly EMPTY_STR='""'

# Stub out a few variables
readonly PREPROC_FLAGS=(
  -D OVM_MAIN \
  -D PYTHONPATH="$EMPTY_STR" \
  -D VERSION="$EMPTY_STR" \
  -D VPATH="$EMPTY_STR" \
  -D Py_BUILD_CORE \
  # Python already has support for disabling complex numbers!
  -D WITHOUT_COMPLEX
)

# NOTE: build/oil-defs is hard-coded to the oil.ovm app.  We're abandoning
# hello.ovm and opy.ovm for now, but those can easily be added later.  We
# haven't mangled the CPython source!
readonly INCLUDE_PATHS=(
  -I .
  -I Include
  -I ../_devbuild/gen
  -I ../build/oil-defs
  -I ../py-yajl
   # Note: This depends on build/dev.sh yajl-release
  -I ../py-yajl/yajl/yajl-2.1.1/include
)
readonly CC=${CC:-cc}  # cc should be on POSIX systems

# BASE_CFLAGS is copied by observation from what configure.ac does on my Ubuntu
# 16.04 system.  Then we check if it works on Alpine Linux too.

# "Python violates C99 rules, by casting between incompatible pointer types.
# GCC may generate bad code as a result of that, so use -fno-strict-aliasing if
# supported."
# - gcc 4.x and Clang need -fwrapv

# TODO:
# - -DNDEBUG is also passed.  That turns off asserts.  Do we want that?
# - We should auto-detect the flags in configure, or simplify the source so it
# isn't necessary.  Python's configure.ac sometimes does it by compiling a test
# file; at other times it does it by grepping $CC --help.

BASE_CFLAGS='-fno-strict-aliasing -fwrapv -Wall -Wstrict-prototypes'

# These flags are disabled for OS X.  I would have thought it would work in
# Clang?  It works with both GCC and Clang on Linux.
# https://stackoverflow.com/questions/6687630/how-to-remove-unused-c-c-symbols-with-gcc-and-ld
#BASE_CFLAGS="$BASE_CFLAGS -fdata-sections -ffunction-sections"

# Needed after cpython-defs filtering.
BASE_CFLAGS="$BASE_CFLAGS -Wno-unused-variable -Wno-unused-function"
readonly BASE_CFLAGS

BASE_LDFLAGS=''
# Disabled for OS X
# BASE_LDFLAGS='-Wl,--gc-sections'

# The user should be able to customize CFLAGS, but it shouldn't disable what's
# in BASE_CFLAGS.
readonly CFLAGS=${CFLAGS:-}
readonly LDFLAGS=${LDFLAGS:-}

build() {
  local out=${1:-$PY27/ovm2}
  local module_init=${2:-$PY27/Modules/config.c}
  local main_name=${3:-_tmp/hello/main_name.c}
  local c_module_srcs=${4:-_tmp/hello/c-module-srcs.txt}
  shift 4

  local abs_out=$PWD/$out
  local abs_module_init=$PWD/$module_init
  local abs_main_name=$PWD/$main_name
  local abs_c_module_srcs=$PWD/$c_module_srcs

  #echo $OVM_LIBRARY_OBJS

  # HAVE_READLINE defined in detected-config.sh.
  source-detected-config-or-die

  pushd $PY27

  local readline_flags=''
  if [[ "$HAVE_READLINE" -eq 1 ]]; then
    # Readline interface for tokenizer.c and [raw_]input() in bltinmodule.c.
    # For now, we are using raw_input() for the REPL.  TODO: Parameterize this!
    # We should create a special no_readline_raw_input().

    c_module_src_list=$(cat $abs_c_module_srcs)

    if [[ -n "$READLINE_DIR" ]]; then
      readline_flags+="-L $READLINE_DIR/lib -I $READLINE_DIR/include "
    fi

    # NOTE: pyconfig.h has HAVE_LIBREADLINE but doesn't appear to use it?
    readline_flags+="-l readline -D HAVE_READLINE"
  else
    # don't fail
    c_module_src_list=$(grep -E -v '/readline.c|/line_input.c' $abs_c_module_srcs || true)
  fi

  # $PREFIX comes from ./configure and defaults to /usr/local.
  # $EXEC_PREFIX is a GNU thing and used in getpath.c.  Could probably get rid
  # of it.

  time $CC \
    ${BASE_CFLAGS} \
    ${CFLAGS} \
    "${INCLUDE_PATHS[@]}" \
    "${PREPROC_FLAGS[@]}" \
    -D PREFIX="\"$PREFIX\"" \
    -D EXEC_PREFIX="\"$PREFIX\"" \
    -o $abs_out \
    $OVM_LIBRARY_OBJS \
    $abs_module_init \
    $abs_main_name \
    $c_module_src_list \
    Modules/ovm.c \
    -l m \
    ${BASE_LDFLAGS} \
    ${LDFLAGS} \
    $readline_flags \
    "$@" \
    || true
  popd

  # TODO: Return proper exit code from this action
  return 0

  # NOTE:
  # -l readline -l termcap -- for Python readline.  Hm it builds without -l
  # termcap.
  # -l z WOULD be needed for zlibmodule.c, but we don't need it because our zip
  # file has no compression -- see build/make_zip.py with ZIP_STORED.
  # zipimport works fine without this.
}

# build the optimized one.  Makefile uses -O3.

# Clang -O2 is 1.37 MB.  18 seconds to compile.
#   -m32 is 1.12 MB.  But I probably have to redefine a few things because
#   there are more warnings.
# -O3 is 1.40 MB.

# GCC -O2 is 1.35 MB.  21 seconds to compile.

build-dbg() {
  build "$@" -O0 -g -D OVM_DEBUG
}

# This will be stripped later.
build-opt() {
  # frame pointer for perf.  Otherwise stack traces are messed up!
  # http://www.brendangregg.com/FlameGraphs/cpuflamegraphs.html#C  But why
  # isn't debuginfo enough?  Because it's a recursive function?
  # Does this make things slower?  Do I need a "perf" build?
  build "$@" -O3 -fno-omit-frame-pointer
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

  cd $PY27

  # -MM: no system headers
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

  # 1. -MM outputs Makefile fragments, so egrep turns those into proper lines.
  #
  # 2. The user should generated detected-config.h, so remove it.
  #
  # 3. # gcc outputs paths like
  # Python-2.7.13/Python/../Objects/stringlib/stringdefs.h
  # but 'Python/..' causes problems for tar.
  #

  # NOTE: need .def for build/oil-defs.
  _headers $c_module_srcs \
    | egrep --only-matching '[^ ]+\.(h|def)' \
    | grep -v '_build/detected-config.h' \
    | sed 's|^Python/../||' \
    | sort | uniq | add-py27
}

make-tar() {
  local app_name=${1:-hello}
  local bytecode_zip=${2:-bytecode-cpython.zip}
  local out=${3:-_release/hello.tar}

  local version_file
  case $app_name in
    oil)
      version_file=oil-version.txt
      ;;
    hello)
      version_file=build/testdata/hello-version.txt
      ;;
    *)
      die "Unknown app $app_name"
      exit 1
      ;;
  esac
  local version=$(head -n 1 $version_file)

  echo "Creating $app_name version $version"

  local c_module_srcs=_build/$app_name/c-module-srcs.txt

  # Add oil-0.0.0/ to the beginning of every path.
  local sed_expr="s,^,${app_name}-${version}/,"

  # Differences between tarball and repo:
  #
  # - portable-rules.mk is intentionally not included in the release tarball.
  #   The Makefile can and should operate without it.
  #
  # - We include intermediate files like c-module-srcs.txt, so we don't have to
  #   ship tools app_deps.py.  The end-user build shouldn't depend on Python.

  tar --create --transform "$sed_expr" --file $out \
    LICENSE.txt \
    INSTALL.txt \
    configure \
    install \
    uninstall \
    Makefile \
    doc/osh.1 \
    build/compile.sh \
    build/actions.sh \
    build/common.sh \
    build/detect-*.c \
    _build/$app_name/$bytecode_zip \
    _build/$app_name/*.c \
    py-yajl/yajl/COPYING \
    $PY27/LICENSE \
    $PY27/Modules/ovm.c \
    $c_module_srcs \
    $(cat $c_module_srcs | add-py27) \
    $(python-headers $c_module_srcs) \
    $(python-sources)

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

if test $(basename $0) = 'compile.sh'; then
  "$@"
fi
