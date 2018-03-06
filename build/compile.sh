#!/usr/bin/env bash
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

# The stuff in Modules/Setup.dist, signalmodule.c.  NOTE: In Python,
# signalmodule.c is specified in Modules/Setup.config, which comes from
# 'configure' output.
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
  -D Py_BUILD_CORE
)

readonly INCLUDE_PATHS=(-I . -I Include -I ../_devbuild/gen)
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

readonly BASE_CFLAGS='-fno-strict-aliasing -fwrapv -Wall -Wstrict-prototypes'

# The user should be able to customize CFLAGS, but it shouldn't disable what's
# in BASE_CFLAGS.
readonly CFLAGS=${CFLAGS:-}

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

  local compile_readline
  local link_readline
  if test "$HAVE_READLINE" = 1; then
    # Readline interface for tokenizer.c and [raw_]input() in bltinmodule.c.
    # For now, we are using raw_input() for the REPL.  TODO: Parameterize this!
    # We should create a special no_readline_raw_input().

    c_module_src_list=$(cat $abs_c_module_srcs)
    # NOTE: pyconfig.h has HAVE_LIBREADLINE but doesn't appear to use it?
    compile_readline='-D HAVE_READLINE'
    link_readline='-l readline'
  else
    # don't fail
    c_module_src_list=$(grep -v '/readline.c' $abs_c_module_srcs || true)
    compile_readline=''
    link_readline=''
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
    $compile_readline \
    -l m \
    $link_readline \
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

  # 1. -MM outputs Makefile fragments, so egrep turns those into proper lines.
  #
  # 2. The user should generated detected-config.h, so remove it.
  #
  # 3. # gcc outputs paths like
  # Python-2.7.13/Python/../Objects/stringlib/stringdefs.h
  # but 'Python/..' causes problems for tar.
  #

  _headers $c_module_srcs \
    | egrep --only-matching '[^ ]+\.h' \
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
    Makefile \
    build/compile.sh \
    build/actions.sh \
    build/common.sh \
    build/detect-*.c \
    _build/$app_name/$bytecode_zip \
    _build/$app_name/*.c \
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

"$@"
