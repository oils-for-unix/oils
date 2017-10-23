#! /bin/bash --
#
# build.sh -- compile StaticPython from sources
# by pts@fazekas.hu at Wed Aug 11 16:49:32 CEST 2010
# Mac OS X support at Sat May 21 21:04:07 CEST 2011
#
# Example invocation: ./build.sh
# Example invocation: ./build.sh stackless
# Example invocation: ./build.sh stacklessco
# Example invocation: ./build.sh stacklessco usessl
# Example invocation: ./build.sh python3.2
# Example invocation: ./build.sh stackless3.2
# Example invocation: ./build.sh stacklessxl3.2
#
# This script has been tested on Ubuntu Hardy, should work on any Linux system.
#
# TODO(pts): Build linux libs from source as well.
# TODO(pts): Run on FreeBSD in Linux. Does epoll in libevent mode? How to avoid it?
#
# To facilitate exit on error,
#
#   (true; false; true; false)
#
# has to be changed to
#
#   (true && false && true && false) || return "$?"  # in bash-3.1.17
#   (true && false && true && false)  # in busybox sh
#
# for Mac OS X:
#
# TODO(pts): Add openssl-based AES encryption module (does it support XTS): https://wiki.openssl.org/index.php/EVP_Symmetric_Encryption_and_Decryption
#            ... or does alo-aes support XTS?
# TODO(pts): Make binaries identical upon recompilation.
# TODO(pts): Implement stacklessco.
# TODO(pts): Configure -lz  --> pyconfig.h HAVE_ZLIB_COPY=1 
# TODO(pts): Verify `import sysconfig' on both Linux and Mac OS X.
# TODO(pts): Get rid of -ldl.
# TODO(pts): Get rid of -framework CoreFoundation.
# TODO(pts): Use libintl.a, but without libiconv.a (too large, 1MB).
# TODO(pts): Add -mtune=cpu-type and -march=cpu-type (with SSE).
# TODO(pts): Test if hard switching works on both Linux and the Mac.
#            --enable-stacklessfewerregisters .
# TODO(pts): Make zipimport keep the .zip file open. (it closes it in Python
#            3.2.)

if true; then  # Make the shell script editable while it's executing.

test "${0%/*}" != "$0" && cd "${0%/*}"

UNAME=$(./busybox uname 2>/dev/null || uname || true)

# To provide a uniform build environment
unset PYTHONPATH PYTHONSTARTUP PYTHONHOME PYTHONCASEOK PYTHONIOENCODING

if test "$NO_BUSYBOX" || test "$UNAME" = Darwin; then  # Darwin is Mac OS X
  BUSYBOX=
  PATCH='patch -t'  # -t to disable prompts.
elif test "$BASH_VERSION" || test -z "$STATICPYTHON_IN_BUSYBOX"; then
  unset BASH_VERSION
  export STATICPYTHON_IN_BUSYBOX=1
  exec ./busybox sh -- "$0" "$@"
else
  BUSYBOX=./busybox
  # Make sure we fail unless we use ./busybox for all non-built-in commands.
  export PATH=/dev/null
  set -e  # Abort on error.
  test -d busybox.bin || ./busybox mkdir busybox.bin
  for F in cp mv rm sleep touch mkdir tar expr sed awk ls pwd test cmp diff \
           patch xz \
           sort cat head tail chmod chown uname basename tr find grep ln; do
    ./busybox rm -f busybox.bin/"$F"
    ./busybox ln -s ../busybox busybox.bin/"$F"
  done
  PATCH=patch  # `busybox patch' doesn't have -t, but it disables prompts by default.
  ./busybox rm -f busybox.bin/make; ./busybox ln -s ../make busybox.bin/make
  ./busybox rm -f busybox.bin/perl; ./busybox ln -s ../perl busybox.bin/perl
  export PATH="$PWD/busybox.bin"
  export SHELL="$PWD/busybox.bin/sh"
fi

set -e  # Abort on error.

# ---

INSTS_BASE="bzip2-1.0.5.inst.tbz2 ncurses-5.6.inst.tbz2 readline-5.2.inst.tbz2 sqlite-3.7.0.1.inst.tbz2 zlib-1.2.3.3.inst.tbz2"

STEPS=
USE_SSL=
USE_TC=
USE_LMDB=
TARGET=python2.7-static
PYTHONTBZ2=Python-2.7.12.tar.xz
IS_CO=
IS_PY3=
for ARG in "$@"; do 
  ARG="${ARG%-static}"  # E.g. convert python2.7-static to python2.7
  if test "$ARG" = stackless || test "$ARG" = stackless2.7; then
    TARGET=stackless2.7-static
    PYTHONTBZ2=stackless-2712-export.tar.xz
    IS_CO=
    IS_XX=
    IS_PY3=
    USE_SSL=
  elif test "$ARG" = stacklessco || test "$ARG" = stacklessco2.7; then
    TARGET=stacklessco2.7-static
    PYTHONTBZ2=stackless-2712-export.tar.xz
    IS_CO=1
    IS_XX=
    ISP_PY3=
    USE_SSL=1
  elif test "$ARG" = stacklessxx || test "$ARG" = stacklessxx2.7; then
    TARGET=stacklessxx2.7-static
    PYTHONTBZ2=stackless-2712-export.tar.xz
    IS_CO=1
    IS_XX=1  # IS_CO=1 must also be set.
    ISP_PY3=
    USE_SSL=1
    USE_TC=1
    USE_LMDB=1
  elif test "$ARG" = python || test "$ARG" = python2.7; then
    TARGET=python2.7-static
    PYTHONTBZ2=Python-2.7.12.tar.xz
    IS_CO=
    IS_XX=
    IS_PY3=
    USE_SSL=
  elif test "$ARG" = python3.2; then
    TARGET=python3.2-static
    PYTHONTBZ2=Python-3.2.tar.bz2
    IS_CO=
    IS_XX=
    IS_PY3=1
    USE_SSL=
  elif test "$ARG" = stackless3.2; then
    TARGET=stackless3.2-static
    PYTHONTBZ2=stackless-32-export.tar.bz2
    IS_CO=
    IS_XX=
    IS_PY3=1
    USE_SSL=
  elif test "$ARG" = stacklessxl3.2; then
    TARGET=stacklessxl3.2-static
    PYTHONTBZ2=stackless-32-export.tar.bz2
    IS_CO=
    IS_XX=
    IS_PY3=1
    USE_SSL=1
  elif test "$ARG" = usessl; then
    USE_SSL=1
  elif test "$ARG" = nossl; then
    USE_SSL=
  else
    STEPS="$STEPS $ARG"
  fi
done
if test -z "$STEPS"; then
  # Don't include betry here.
  # Please note that fixsetup appears multiple times here. This is intentional,
  # to get Modules/Setup right.
  STEPS="initbuilddir initdeps buildlibssl buildlibevent2 buildlibtc configure fixsemaphore patchsetup fixsetup patchimport patchgetpath patchsqlite patchssl patchlocale fixsetup makeminipython extractpyrex patchsyncless patchgevent patchgeventmysql patchmsgpack patchpythontokyocabinet patchpythonlmdb patchconcurrence patchpycrypto patchaloaes fixsetup makepython buildpythonlibzip buildtarget"
fi

INSTS="$INSTS_BASE"
BUILDDIR="$TARGET.build"
PBUILDDIR="$PWD/$BUILDDIR"

# GNU Autoconf's ./configure uses $CC, $LD, $AR, $LDFLAGS and $RANLIB to
# generate the Makefile.
if test "$UNAME" = Darwin; then
  # -march=i386 wouldn't work, it would disable SSE. So we use -m32.
  export CC="gcc-mp-4.4 -m32 -static-libgcc -I$PBUILDDIR/build-include"
  export AR=ar
  export RANLIB=ranlib
  export LD=ld
  export LDFLAGS="-L$PBUILDDIR/build-lib"

  export STRIP=strip
else
  export CC="$PBUILDDIR/cross-compiler-i686/bin/i686-gcc -static -fno-stack-protector"
  export AR="$PBUILDDIR/cross-compiler-i686/bin/i686-ar"
  export RANLIB="$PBUILDDIR/cross-compiler-i686/bin/i686-ranlib"
  export LD="$PBUILDDIR/cross-compiler-i686/bin/i686-ld"  # The ./configure script of libevent2 fails without $LD being set.
  export LDFLAGS=""

  export STRIP="$PBUILDDIR/cross-compiler-i686/bin/i686-strip -s"
fi

echo "Running in directory: $PWD"
echo "Building target: $TARGET"
echo "Building in directory: $BUILDDIR"
echo "Using Python source distribution: $PYTHONTBZ2"
echo "Will run steps: $STEPS"
echo "Is adding coroutine libraries: $IS_CO"
echo "Is using OpenSSL for SSL functionality: $USE_SSL"
echo "Is using Tokyo Cabinet database: $USE_TC"
echo "Is using LMDB (database): $USE_LMDB"
echo "Operating system UNAME: $UNAME"
echo

initbuilddir() {
  rm -rf "$BUILDDIR" || return "$?"
  mkdir "$BUILDDIR" || return "$?"

  if test "$UNAME" = Linux || test "$UNAME" = Darwin; then
    :
  else
    set +x
    echo "fatal: unsupported operating system: $UNAME" >&2
    return 2
  fi

  if test "$UNAME" = Darwin; then
    mkdir "$BUILDDIR/build-include" || return "$?"
    mkdir "$BUILDDIR/build-lib" || return "$?"
  else
    ( cd "$BUILDDIR" || return "$?"
      mkdir cross-compiler-i686 || return "$?"
      cd cross-compiler-i686 || return "$?"
      tar xjvf ../../gcxbase.inst.tbz2 || return "$?"
      tar xjvf ../../gcc.inst.tbz2 || return "$?"
      tar xjvf ../../gcxtool.inst.tbz2 || return "$?"
    ) || return "$?"
  fi

  # Set up a fake config.guess for operating system and architecture detection.
  #
  # This is to make sure that we have i686 even on an x86_64 host for Linux.
  if test "$UNAME" = Darwin; then
    (echo '#!/bin/sh'; echo 'echo i386-apple-darwin9.8.0') >"$BUILDDIR/config.guess.fake" || return "$?"
  else
    (echo '#!/bin/sh'; echo 'echo i686-pc-linux-gnu') >"$BUILDDIR/config.guess.fake" || return "$?"
  fi
  chmod +x "$BUILDDIR/config.guess.fake" || return "$?"

  # Check the C compiler.
  (echo '#include <stdio.h>'
   echo 'main() { return!printf("Hello, World!\n"); }'
  ) >"$BUILDDIR/hello.c" || return "$?"
  if ! $CC -o "$BUILDDIR/hello" "$BUILDDIR/hello.c"; then
    set +x
    echo "fatal: the C compiler doesn't work" >&2
    if test "$UNAME" = Darwin; then
      echo "info: did you install MacPorts and run: sudo port install gcc44" >&2
    fi
    exit 2
  fi
  $STRIP "$BUILDDIR/hello" || return "$?"
  local OUT="$("$BUILDDIR/hello")"
  test "$?" = 0
  test "$OUT" = "Hello, World!"

  ( cd "$BUILDDIR" || return "$?"
    if test "${PYTHONTBZ2%.xz}" != "${PYTHONTBZ2}"; then
      xz -d <../"$PYTHONTBZ2" | tar xv || return "$?"
    else
      tar xjvf ../"$PYTHONTBZ2" || return "$?"
    fi
  ) || return "$?"
  ( cd "$BUILDDIR" || return "$?"
    if test -d Python-*; then
      mv Python-*/* . || return "$?"
    elif test -d python-*; then
      mv python-*/* . || return "$?"
    elif test -d stackless-*; then
      mv stackless-*/* . || return "$?"
    fi
    # Disabling this build rule is needed for python-2.7.12.
    perl -pi~ -e 's@^(Parser/pgenmain[.]o:)@disabled_$1@' Makefile.pre.in || return "$?"
  ) || return "$?"

  ( cd "$BUILDDIR/Modules" || return "$?"
    tar xzvf ../../greenlet-0.3.1.tar.gz || return "$?"
    if test "$IS_PY3"; then
      # TODO(pts): Copy patch(1) this to the Mac OS X chroot.
      $PATCH -p0 <../../greenlet-0.3.1-pycapsule.patch || return "$?"
    fi
  ) || return "$?"

  ( cd "$BUILDDIR" || return "$?"
    mkdir -p advzip || return "$?"
    cd advzip || return "$?"
    if test "$UNAME" = Darwin; then
      tar xjvf ../../advzip.darwin.inst.tbz2 || return "$?"
    else
      tar xjvf ../../advzip.inst.tbz2 || return "$?"
    fi
  ) || return "$?"

  cp -f "$BUILDDIR/config.guess.fake" "$BUILDDIR/config.guess"
}

initdeps() {
  if test "$UNAME" = Darwin; then  # Mac OS X
    builddeps || return "$?"
  else  # Linux
    extractinsts || return "$?"
  fi
  # These are moved to $STEPS:
  #buildlibssl     # Needs libz if enabled.
  #buildlibevent2  # Needs libssl if enabled.
  #buildlibtc      # Needs libz and libbz2 if enabled.
}

builddeps() {
  # The `|| return "$?"' clauses are needed by bash 3.2.17 on Mac OS X.
  # This is an alternative to extractinsts
  buildlibz || return "$?"
  buildlibbz2 || return "$?"
  buildlibreadline || return "$?"
  buildlibsqlite3 || return "$?"
  buildlibevent2 || return "$?"
}

buildlibbz2() {
  ( cd "$BUILDDIR" || return "$?"
    rm -rf bzip2-1.0.6 || return "$?"
    tar xzvf ../bzip2-1.0.6.tar.gz || return "$?"
    cd bzip2-1.0.6 || return "$?"
    perl -pi~ -e 's@\s-g(?!\S)@@g, s@\s-O\d*(?!\S)@ -O3@g if s@^CFLAGS\s*=@CFLAGS = @' Makefile || return "$?"
    make CC="$CC" || return "$?"
    cp libbz2.a ../build-lib/libbz2-staticpython.a || return "$?"
    cp bzlib.h ../build-include/ || return "$?"
  ) || return "$?"
}

buildlibtc() {
  test "$USE_TC" || return 0
  ( cd "$BUILDDIR" || return "$?"
    rm -rf tokyocabinet-1.4.47 || return "$?"
    tar xzvf ../tokyocabinet-1.4.47.tar.gz || return "$?"
    cd tokyocabinet-1.4.47 || return "$?"
    #if test "$UNAME" = Darwin; then
    #  : No support for xx on Darwin.  # See below.
    #  return 1
    #fi
    # TODO(pts): Add -staticpython for libz and libbz2 on Darwin:
    # LIBS="-lbz2  $LIBS"
    # LIBS="-lz  $LIBS"
    if test "$UNAME" = Darwin; then
      # The configure script doesn't seem to care much.
      # This seems to work even on Linux.
      perl -pi~ -e 's@^ *(LIBS="-l(?:z|bz2))@$1-staticpython @' configure || return "$?"
    fi
    # TODO(pts): Check
    perl -pi~ -e 's@nanl\([^()]*\)@NAN@g' *.c || return "$?"  # There is no nanl(...) function in uClibc.
    ./configure --prefix=/dev/null/missing --disable-shared || return "$?"
    perl -pi~ -e 's@\s-g(?!\S)@@g, s@\s-O\d*(?!\S)@ -O2@g if s@^CFLAGS\s*=@CFLAGS = @; s@ -I\S+@ @g, s@=@= -I.@ if s@^CPPFLAGS\s*=\s*@CPPFLAGS = @' Makefile || return "$?"
    make libtokyocabinet.a || return "$?"
    $RANLIB libtokyocabinet.a || return "$?"
    cp libtokyocabinet.a ../build-lib/libtokyocabinet-staticpython.a || return "$?"
    # tcadb.h  tcbdb.h  tcfdb.h  tchdb.h  tctdb.h  tcutil.h
    # Don't copy: md5.h myconf.h
    cp tc*.h ../build-include/ || return "$?"
  ) || return "$?"
}

buildlibreadline() {
  ( cd "$BUILDDIR" || return "$?"
    rm -rf readline-5.2 || return "$?"
    tar xzvf ../readline-5.2.tar.gz || return "$?"
    cd readline-5.2 || return "$?"
    ./configure --disable-shared || return "$?"
    perl -pi~ -e 's@\s-g(?!\S)@@g, s@\s-O\d*(?!\S)@ -O2@g if s@^CFLAGS\s*=@CFLAGS = @' Makefile || return "$?"
    make || return "$?"
    # We could copy history.a, but Python doesn't need it.
    cp libreadline.a ../build-lib/libreadline-staticpython.a || return "$?"
    rm -rf ../build-include/readline || return "$?"
    mkdir ../build-include/readline || return "$?"
    cp rlstdc.h rltypedefs.h keymaps.h tilde.h readline.h history.h chardefs.h ../build-include/readline/ || return "$?"
  ) || return "$?"
}

buildlibsqlite3() {
  ( cd "$BUILDDIR" || return "$?"
    rm -rf sqlite-amalgamation-3070603 || return "$?"
    unzip ../sqlite-amalgamation-3070603.zip || return "$?"
    cd sqlite-amalgamation-3070603 || return "$?"
    $CC -c -O2 -DSQLITE_ENABLE_STAT2 -DSQLITE_ENABLE_FTS3 -DSQLITE_ENABLE_FTS4 -DSQLITE_ENABLE_RTREE -W -Wall sqlite3.c || return "$?"
    $AR cr libsqlite3.a sqlite3.o || return "$?"
    $RANLIB libsqlite3.a || return "$?"
    cp libsqlite3.a ../build-lib/libsqlite3-staticpython.a || return "$?"
    cp sqlite3.h ../build-include/ || return "$?"
  ) || return "$?"
}

buildlibz() {
  ( cd "$BUILDDIR" || return "$?"
    rm -rf zlib-1.2.5 || return "$?"
    tar xjvf ../zlib-1.2.5.tar.bz2 || return "$?"
    cd zlib-1.2.5 || return "$?"
    ./configure --static || return "$?"
    perl -pi~ -e 's@\s-g(?!\S)@@g, s@\s-O\d*(?!\S)@ -O3@g if s@^CFLAGS\s*=@CFLAGS = @' Makefile || return "$?"
    make || return "$?"
    cp libz.a ../build-lib/libz-staticpython.a || return "$?"
    cp zconf.h zlib.h ../build-include/ || return "$?"
  ) || return "$?"
}

buildlibssl() {
  test "$USE_SSL" || return 0
  ( cd "$BUILDDIR" || return "$?"
    rm -rf openssl-0.9.8zh.tar.gz || return "$?"
    tar xzvf ../openssl-0.9.8zh.tar.gz || return "$?"
    cd openssl-0.9.8zh || return "$?"
    if test "$UNAME" = Linux; then
      ./Configure no-shared linux-elf no-dso || return "$?"
    else
      # This inserts `-arch i386', which we remove below.
      ./Configure no-shared darwin-i386-cc || return "$?"  # TODO(pts): Test this.
    fi
    # Doing -O3 instead of -O2 would increase the binary size by about 67 KiB
    # for openssl-0.9.8zh.tar.gz , and it would speed up hashlib.pbkdf2_hmac
    # by about 1.5% (most of the hash computation is already in assembly). Not
    # doing it.
    perl -pi~ -e 's@\s(?:-g|-arch\s+\S+)(?!\S)@@g, s@\s-O\d*(?!\S)@ -O2@g, s@\s-D(DSO_DLFCN|HAVE_DLFCN_H)(?!\S)@@g if s@^CFLAG\s*=\s*@CFLAG = @' Makefile || return "$?"
    # Workaround for our perl not supporting -I... and PERLINC=...
    ln -s . crypto/des/asm/perlasm || return "$?"
    make build_libs || return "$?"
    cp libssl.a ../build-lib/libssl-staticpython.a || return "$?"
    cp libcrypto.a ../build-lib/libcrypto-staticpython.a || return "$?"
    mkdir ../build-include/openssl || return "$?"
    cp include/openssl/*.h ../build-include/openssl/ || return "$?"
  ) || return "$?"
}

buildlibevent2() {
  test "$IS_CO" || return 0
  ( cd "$BUILDDIR" || return "$?"
    rm -rf libevent-2.0.16-stable || return "$?"
    rm -rf build-include/event2 || return "$?"
    rm -rf build-lib/libevent* || return "$?"
    tar xzvf ../libevent-2.0.16-stable.tar.gz || return "$?"
    cd libevent-2.0.16-stable || return "$?"
    local SSL_FLAGS=--disable-openssl
    if test "$USE_SSL"; then
      SSL_FLAGS=--enable-openssl
      perl -pi~ -e 's@^for ac_lib in \x27\x27 ssl;@for ac_lib in \x27\x27 \x27ssl-staticpython -lcrypto-staticpython\x27;@;
                    s@ -lcrypto(?= )@ -lcrypto-staticpython@g' configure || return "$?"
    fi
    ./configure $SSL_FLAGS --disable-debug-mode --disable-shared --disable-libevent-regress || return "$?"
    if test "$USE_SSL"; then
      grep '^#define HAVE_OPENSSL 1$' config.h || return "$?"
    fi
    cp -f ../config.guess.fake config.guess
    perl -pi~ -e 's@\s-g(?!\S)@@g, s@\s-O\d*(?!\S)@ -O2@g if s@^CFLAGS\s*=@CFLAGS = @' Makefile */Makefile || return "$?"
    make ./include/event2/event-config.h libevent_core.la libevent.la || return "$?"
    $AR cr  libevent_evhttp.a bufferevent_sock.o http.o listener.o || return "$?"
    $RANLIB libevent_evhttp.a || return "$?"
    cp .libs/libevent_core.a ../build-lib/libevent_core-staticpython.a || return "$?"
    cp libevent_evhttp.a ../build-lib/libevent_evhttp-staticpython.a || return "$?"
    mkdir ../build-include/event2 || return "$?"
    cp include/event2/*.h ../build-include/event2/ || return "$?"
  ) || return "$?"
}

extractinsts() {
  for INSTTBZ2 in $INSTS; do
    ( cd "$BUILDDIR/cross-compiler-i686" || return "$?"
      tar xjvf ../../"$INSTTBZ2" || return "$?"
    ) || return "$?"
  done
  # These symlinks are needed for the build commands below on Linux.
  if test "$UNAME" = Linux; then
    ln -s cross-compiler-i686/lib     "$BUILDDIR/build-lib"
    ln -s cross-compiler-i686/include "$BUILDDIR/build-include"
  fi
}

configure() {
  ( cd "$BUILDDIR" || return "$?"
    # TODO(pts): Make sure x86 is detected (not x86_64).
    # This removal makes Python-ast.c not autogenerated. Autogeneration would
    # need a working Python binary, which we don't have yet.
    perl -pi -e '$_="" if /ASDLGEN/' Makefile.pre.in
    local REGSFLAGS=
    # Without --enable-stacklessfewerregisters, we'd get the error:
    #  ./Stackless/platf/switch_x86_unix.h:37: error: PIC register 'ebx' clobbered in 'asm'
    test "$UNAME" = Darwin && REGSFLAGS=--enable-stacklessfewerregisters
    ./configure --disable-shared --disable-ipv6 $REGSFLAGS || return "$?"
  ) || return "$?"
  fixmakefile
}

fixsemaphore() {
  ( cd "$BUILDDIR" || return "$?"
    if test "$UNAME" = Linux; then
      # The ./configure script doesn't detect proper semaphores on Linux uClibc.
      #
      # It does detect on Darwin.
      perl -pi -e 's@^#define POSIX_SEMAPHORES_NOT_ENABLED 1$@/* #undef POSIX_SEMAPHORES_NOT_ENABLED */@' \
          pyconfig.h || return "$?"
    fi
  ) || return "$?"
}

fixmakefile() {
  ( cd "$BUILDDIR" || return "$?"
    # `-framework CoreFoundation' is good to be removed on the Mac OS X, to
    # prevent additional .dylib dependencies on
    # /System//Library/Frameworks/CoreFoundation.framework/Versions/A/CoreFoundation
    # .
    perl -pi~ -e 's@\s-(?:ldl|framework\s+CoreFoundation)(?!\S)@@g if s@^LIBS\s*=@LIBS = @' Makefile || return "$?"
    # Remove -O... and -g from CFLAGS and OPT, and add -O2 to OPT. Please note
    # that Python 3.2 doesn't have CFLAGS at all.
    perl -pi~ -e 's@\s-(?:g|O\d*)(?!\S)@@g, s@$@ -O2@ if s@^OPT\s*=@OPT = @' Makefile || return "$?"
    perl -pi~ -e 's@\s-(?:g|O\d*)(?!\S)@@g, s@$@ -O2@ if s@^SLPFLAGS\s*=@SLPFLAGS = @' Makefile || return "$?"
    perl -pi~ -e 's@\s-g(?!\S)@@g, s@\s-O\d*(?!\S)@@g if s@^CFLAGS\s*=@CFLAGS = @' Makefile || return "$?"
    if test "$IS_PY3"; then
      if ! grep '@SLPFLAGS@' Makefile; then
        :
      elif test "$UNAME" = Darwin; then
        # Fix for Stackless 3.2.
        # TODO(pts): Run all Stackless test to verify this.
        perl -pi~ -e 's~\@SLPFLAGS\@~-fomit-frame-pointer -DSTACKLESS_FRHACK=1 -O2~g' Makefile || return "$?"
      else
        perl -pi~ -e 's~\@SLPFLAGS\@~-fno-omit-frame-pointer -O2~g' Makefile || return "$?"
      fi
    fi
  ) || return "$?"
}

patchsetup() {
  # This must be run after the configure step, because configure overwrites
  # Modules/Setup
  if test "$IS_PY3"; then
    cp Modules.Setup.3.2.static "$BUILDDIR/Modules/Setup" || return "$?"
  else
    cp Modules.Setup.2.7.static "$BUILDDIR/Modules/Setup" || return "$?"
  fi
  # Please note that fixsetup has to be called now, partially because of
  # fixing the Makefile.
}

fixsetup() {
  if test "$UNAME" = Darwin; then
    # * /usr/lib/libncurses.5.dylib
    # * _locale is disabled because -lintl needs -liconv, which is too large
    #   (1MB)
    # * spwd is disabled because the Mac OS X doesn't contain
    #   /usr/include/shadow.h .
    # * -lcrypt and -lm are not necessary in the Mac OS X, everything is in
    #   the libc.
    # * -lz, -lsqlite3, -lreadline and -lbz2 have to be converted to
    #   -l...-staticpython so that out lib*-staticpython.a would be selected.
    perl -pi~ -e '
        s@\s-lncurses\S*@ -lncurses.5@g;
        s@^(?:_locale|spwd)(?!\S)@#@; s@\s-(?:lcrypt|lm)(?!\S)@@g;
        s@\s-(lz|lsqlite3|lreadline|lbz2)(?!\S)@ -$1-staticpython@g;
        ' "$BUILDDIR/Modules/Setup" || return "$?"
  fi
  perl -pi~ -e 's@\s-(levent_core|levent_evhttp)(?!\S)@ -$1-staticpython@g' "$BUILDDIR/Modules/Setup" || return "$?"
  sleep 2 || return "$?"  # Wait 2 seconds after the configure script creating Makefile.
  touch "$BUILDDIR/Modules/Setup" || return "$?"
  # We need to run `make Makefile' to rebuild it using our Modules/Setup
  ( cd "$BUILDDIR" || return "$?"
    make Makefile || return "$?"
  ) || return "$?"
  fixmakefile
  if test "$IS_PY3"; then
    ( cd "$BUILDDIR" || return "$?"
      grep '^_thread ' Modules/Setup.config || return "$?"
      grep 'signal' Modules/Setup.config || return "$?"
    ) || return "$?"
  fi
}

patchimport() {
  # This patch is idempotent.
  perl -pi~ -e 's@#ifdef HAVE_DYNAMIC_LOADING(?!_NOT)@#ifdef HAVE_DYNAMIC_LOADING_NOT  /* StaticPython */@g' "$BUILDDIR"/Python/import.c "$BUILDDIR"/Python/importdl.c || return "$?"
}

patchgetpath() {
  # This patch is idempotent.
  # TODO(pts): Make sure that the source string is there for patching.
  # TODO(pts): Make this repatch if calculate_path.*.c is modified.
  perl -pi~ -0777 -e 's@\s+static\s+void\s+calculate_path(?!   )\s*\(\s*void\s*\)\s*{@\n\nstatic void calculate_path(void);  /* StaticPython */\nstatic void calculate_path_not(void) {@g' "$BUILDDIR"/Modules/getpath.c || return "$?"
  if ! grep -q StaticPython-appended "$BUILDDIR/Modules/getpath.c"; then
    if test "$IS_PY3"; then
      cat calculate_path.3.2.c >>"$BUILDDIR/Modules/getpath.c" || return "$?"
    else
      cat calculate_path.2.7.c >>"$BUILDDIR/Modules/getpath.c" || return "$?"
    fi
  fi
}

patchsqlite() {
  # This patch is idempotent.
  if ! grep '^#define MODULE_NAME ' "$BUILDDIR/Modules/_sqlite/util.h"; then
    perl -pi~ -0777 -e 's@\n#define PYSQLITE_UTIL_H\n@\n#define PYSQLITE_UTIL_H\n#define MODULE_NAME "_sqlite3"  /* StaticPython */\n@' "$BUILDDIR/Modules/_sqlite/util.h" || return "$?"
  fi    
  for F in "$BUILDDIR/Modules/_sqlite/"*.c; do
    if ! grep -q '^#include "util.h"' "$F"; then
      perl -pi~ -0777 -e 's@\A@#include "util.h"  /* StaticPython */\n@' "$F" || return "$?"
    fi    
  done
}

generate_loader_py() {
  local CEXT_MODNAME="$1"
  local PY_MODNAME="$2"
  local PY_FILENAME="Lib/${PY_MODNAME//.//}.py"
  : Generating loader "$PY_FILENAME"
  echo "import sys; import $CEXT_MODNAME; sys.modules[__name__] = $CEXT_MODNAME" >"$PY_FILENAME" || return "$?"
}

patch_and_copy_cext() {
  local SOURCE_C="$1"
  local TARGET_C="$2"
  local CEXT_MODNAME="${TARGET_C%.c}"
  export CEXT_MODNAME="${CEXT_MODNAME##*/}"
  export CEXT_MODNAME="${CEXT_MODNAME//._/_}"
  export CEXT_MODNAME="${CEXT_MODNAME//./_}"
  export CEXT_MODNAME=_"${CEXT_MODNAME#_}"
  : Copying and patching "$SOURCE_C" to "$TARGET_C", CEXT_MODNAME="$CEXT_MODNAME"
  <"$SOURCE_C" >"$TARGET_C" perl -0777 -pe '
    s@^(PyMODINIT_FUNC)\s+\w+\(@$1 init$ENV{CEXT_MODNAME}(@mg;
    s@( Py_InitModule\d*)\(\s*"\w[\w.]*",@$1("$ENV{CEXT_MODNAME}",@g;
    # Cython version of the one below.
    s@( Py_InitModule\d*\(\s*__Pyx_NAMESTR\()"\w[\w.]*"\),@$1"$ENV{CEXT_MODNAME}"),@g;
    # For PyCrypto.
    s@^[ \t]*(#[ \t]*define\s+MODULE_NAME\s+\S+)@#define MODULE_NAME $ENV{CEXT_MODNAME}@mg;
    s@^[ \t]*(#[ \t]*define\s+MODULE_NAME\s+\S+.*triple DES.*)@#define MODULE_NAME _Crypto_Cipher_DES3@mg;
  ' || return "$?"
}

enable_module() {
  local CEXT_MODNAME="$1"
  export CEXT_MODNAME
  : Enabling module: "$CEXT_MODNAME"
  grep -qE "^#?$CEXT_MODNAME " Modules/Setup || return "$?"
  perl -0777 -pi -e 's@^#$ENV{CEXT_MODNAME} @$ENV{CEXT_MODNAME} @mg' Modules/Setup || return "$?"
}

patchssl() {
  test "$USE_SSL" || return 0
  ( cd "$BUILDDIR" || return "$?"
    enable_module _ssl || return "$?"
    enable_module _hashlib || return "$?"
  ) || return "$?"
}

patchsyncless() {
  test "$IS_CO" || return 0
  ( cd "$BUILDDIR" || return "$?"
    rm -rf syncless-* syncless.dir Lib/syncless Modules/syncless || return "$?"
    tar xzvf ../syncless-0.25.tar.gz || return "$?"
    mv syncless-0.25 syncless.dir || return "$?"
    mkdir Lib/syncless Modules/syncless || return "$?"
    cp syncless.dir/syncless/*.py Lib/syncless/ || return "$?"
    generate_loader_py _syncless_coio syncless.coio || return "$?"
    patch_and_copy_cext syncless.dir/coio_src/coio.c Modules/syncless/_syncless_coio.c || return "$?"
    cp syncless.dir/coio_src/coio_minihdns.c \
       syncless.dir/coio_src/coio_minihdns.h \
       syncless.dir/coio_src/coio_c_*.h \
       Modules/syncless/ || return "$?"
    enable_module _syncless_coio || return "$?"
  ) || return "$?"
}

patchgevent() {
  test "$IS_CO" || return 0
  ( cd "$BUILDDIR" || return "$?"
    rm -rf gevent-* gevent.dir Lib/gevent Modules/gevent || return "$?"
    tar xzvf ../gevent-0.13.6.tar.gz || return "$?"
    mv gevent-0.13.6 gevent.dir || return "$?"
    mkdir Lib/gevent Modules/gevent || return "$?"
    cp gevent.dir/gevent/*.py Lib/gevent/ || return "$?"
    rm -f gevent.dir/gevent/win32util.py || return "$?"
    generate_loader_py _gevent_core gevent.core || return "$?"
    patch_and_copy_cext gevent.dir/gevent/core.c Modules/gevent/_gevent_core.c || return "$?"
    cat >Modules/gevent/libevent.h <<'END' || return "$?"
/**** pts ****/
#include "sys/queue.h"
#define LIBEVENT_HTTP_MODERN
#include "event2/event.h"
#include "event2/event_struct.h"
#include "event2/event_compat.h"
#include "event2/http.h"
#include "event2/http_compat.h"
#include "event2/http_struct.h"
#include "event2/buffer.h"
#include "event2/buffer_compat.h"
#include "event2/dns.h"
#include "event2/dns_compat.h"
#define EVBUFFER_DRAIN evbuffer_drain
#define EVHTTP_SET_CB  evhttp_set_cb
#define EVBUFFER_PULLUP(BUF, SIZE) evbuffer_pullup(BUF, SIZE)
#define current_base event_global_current_base_
#define TAILQ_GET_NEXT(X) TAILQ_NEXT((X), next)
extern void *current_base;
END
    enable_module _gevent_core || return "$?"
  ) || return "$?"
}

patchgeventmysql() {
  test "$IS_CO" || return 0
  ( cd "$BUILDDIR" || return "$?"
    rm -rf geventmysql-* geventmysql.dir Lib/geventmysql Modules/geventmysql || return "$?"
    tar xjvf ../geventmysql-20110201.tbz2 || return "$?"
    mv gevent-MySQL geventmysql.dir || return "$?"
    mkdir Lib/geventmysql Modules/geventmysql || return "$?"
    cp geventmysql.dir/lib/geventmysql/*.py Lib/geventmysql/ || return "$?"
    generate_loader_py _geventmysql_mysql geventmysql._mysql || return "$?"
    patch_and_copy_cext geventmysql.dir/lib/geventmysql/geventmysql._mysql.c Modules/geventmysql/geventmysql._mysql.c || return "$?"
    enable_module _geventmysql_mysql || return "$?"
  ) || return "$?"
}

run_pyrexc() {
  PYTHONPATH="$PBUILDDIR/Lib:$PWD/pyrex.dir" "$PBUILDDIR"/minipython -S -W ignore::DeprecationWarning -c "from Pyrex.Compiler.Main import main; main(command_line=1)" "$@" || return "$?"
}

#** Equivalent to zip -9r "$@"
#** Usage: run_mkzip filename.zip file_or_dir ...
run_mkzip() {
  # advzip produces smaller files than `zip -9r', because advzip uses the
  # 7-Zip implementation of zip.
  rm -f "$1" || return "$?"  # The .zip file.
  "$PBUILDDIR/advzip/bin/advzip" -a -4 "$@" || return "$?"
}

# Like run_mkzip, but uses Python instead of advzip.
old_run_mkzip() {
  local PYTHON="$PBUILDDIR"/python.exe
  test -f "$PBUILDDIR"/minipython && PYTHON="$PBUILDDIR"/minipython
  # python.exe is for the Mac OS X (case insensitive, vs Python/)
  PYTHONPATH="$PBUILDDIR/Lib" "$PYTHON" -S -c 'if 1:
  import os
  import os.path
  import stat
  import sys
  import zipfile
  def All(filename):
    s = os.lstat(filename)
    assert not stat.S_ISLNK(s.st_mode), filename
    if stat.S_ISDIR(s.st_mode):
      for entry in os.listdir(filename):
        for filename2 in All(os.path.join(filename, entry)):
          yield filename2
    else:
      yield filename
  zip_filename = sys.argv[1]
  zipfile.zlib.Z_DEFAULT_COMPRESSION = 9  # Maximum effort.
  z = zipfile.ZipFile(zip_filename, "w", compression=zipfile.ZIP_DEFLATED)
  for filename in sys.argv[2:]:
    for filename2 in All(filename):
      z.write(filename2)
  z.close()' "$@" || return "$?"
}

patchpythontokyocabinet() {
  test "$USE_TC" || return 0
  ( cd "$BUILDDIR" || return "$?"
    rm -rf python-tokyocabinet-* tokyocabinet.dir Lib/tokyocabinet Modules/tokyocabinet || return "$?"
    tar xjvf ../python-tokyocabinet-20111221.tar.bz2 || return "$?"
    mv python-tokyocabinet-20111221 tokyocabinet.dir || return "$?"
    mkdir Lib/tokyocabinet Modules/tokyocabinet || return "$?"
    #cp tokyocabinet.dir/tokyocabinet/hash.c ../hash.c.orig
    (cd tokyocabinet.dir/tokyocabinet && $PATCH -p0 <../../../tokyocabinet_hash_c.patch) || return "$?"
    # This is just an empty __init__.py.
    cp tokyocabinet.dir/tokyocabinet/*.py Lib/tokyocabinet/ || return "$?"
    local M
    for M in btree hash table; do
      patch_and_copy_cext tokyocabinet.dir/tokyocabinet/$M.c Modules/tokyocabinet/_tokyocabinet_$M.c || return "$?"
      generate_loader_py _tokyocabinet_$M tokyocabinet.$M || return "$?"
      enable_module _tokyocabinet_$M || return "$?"
    done
  ) || return "$?"
}

patchpythonlmdb() {
  test "$USE_LMDB" || return 0
  ( cd "$BUILDDIR" || return "$?"
    rm -rf lmdb-* lmdb.dir Lib/lmdb Modules/lmdb || return "$?"
    tar xzvf ../lmdb-0.92.tar.gz || return "$?"
    mv lmdb-0.92 lmdb.dir || return "$?"
    mkdir Lib/lmdb Modules/lmdb || return "$?"
    echo 'from _lmdb_cpython import *
from _lmdb_cpython import open
from _lmdb_cpython import __all__' >Lib/lmdb/__init__.py
    cp lmdb.dir/lmdb/tool.py Lib/lmdb/ || return "$?"
    cp lmdb.dir/lib/mdb.c Modules/lmdb/lmdb_mdb.c || return "$?"
    cp lmdb.dir/lib/midl.c Modules/lmdb/lmdb_midl.c || return "$?"
    # Our uClibc doesn't support pthread_mutexattr_setpshared, so we just skip the call.
    perl -pi~ -e 's@(pthread_mutexattr_setpshared\()@0&&$1@g' Modules/lmdb/lmdb_mdb.c || return "$?"
    patch_and_copy_cext lmdb.dir/lmdb/cpython.c Modules/lmdb/_lmdb_cpython.c || return "$?"
    #generate_loader_py _lmdb lmdb.btree || return "$?"
    enable_module _lmdb_cpython || return "$?"
  ) || return "$?"
}

extractpyrex() {
  test "$IS_CO" || return 0
  ( cd "$BUILDDIR" || return "$?"
    rm -rf pyrex.dir
    tar xzvf ../Pyrex-0.9.9.tar.gz || return "$?"
    mv Pyrex-0.9.9 pyrex.dir || return "$?"
  ) || return "$?"
}

# Depends on extractpyrex.
patchmsgpack() {
  test "$IS_XX" || return 0
  ( cd "$BUILDDIR" || return "$?"
    rm -rf msgpack-* msgpack.dir Lib/msgpack Modules/msgpack || return "$?"
    tar xjvf ../msgpack-python-20111221.tar.bz2 || return "$?"
    mv msgpack-python-20111221 msgpack.dir || return "$?"
    local VERSION=$(grep '^version = ' msgpack.dir/setup.py)
    test "$VERSION" || return "$?"
    (cd msgpack.dir/msgpack && $PATCH -p0 <../../../msgpack_pyx.patch) || return "$?"
    mv msgpack.dir/msgpack/_msgpack.pyx msgpack.dir/msgpack/_msgpack_msgpack.pyx || return "$?"
    run_pyrexc msgpack.dir/msgpack/_msgpack_msgpack.pyx || return "$?"
    mkdir Lib/msgpack Modules/msgpack || return "$?"
    echo "$VERSION" >Lib/msgpack/__version__.py || return "$?"
    cp msgpack.dir/msgpack/__init__.py Lib/msgpack/ || return "$?"
    cp msgpack.dir/msgpack/_msgpack_msgpack.c msgpack.dir/msgpack/*.h Modules/msgpack/ || return "$?"
    generate_loader_py _msgpack_msgpack msgpack._msgpack || return "$?"
    enable_module _msgpack_msgpack || return "$?"
  ) || return "$?"
}

# Depends on extractpyrex.
patchconcurrence() {
  test "$IS_CO" || return 0
  ( cd "$BUILDDIR" || return "$?"
    rm -rf concurrence-* concurrence.dir Lib/concurrence Modules/concurrence || return "$?"
    tar xzvf ../concurrence-0.3.1.tar.gz || return "$?"
    mv concurrence-0.3.1 concurrence.dir || return "$?"
    mkdir Lib/concurrence Modules/concurrence || return "$?"
    # TODO(pts): Fail if any of the pipe commands fail.
    (cd concurrence.dir/lib && tar c $(find concurrence -type f -iname '*.py')) |
        (cd Lib && tar x) || return "$?"

    generate_loader_py _concurrence_event concurrence._event || return "$?"
    cat >Modules/concurrence/event.h <<'END'
/**** pts ****/
#include <event2/event.h>
#include <event2/event_struct.h>
#include <event2/event_compat.h>
END
    run_pyrexc concurrence.dir/lib/concurrence/concurrence._event.pyx || return "$?"
    patch_and_copy_cext concurrence.dir/lib/concurrence/concurrence._event.c Modules/concurrence/concurrence._event.c || return "$?"
    enable_module _concurrence_event || return "$?"

    generate_loader_py _concurrence_io_io concurrence.io._io || return "$?"
    run_pyrexc concurrence.dir/lib/concurrence/io/concurrence.io._io.pyx || return "$?"
    patch_and_copy_cext concurrence.dir/lib/concurrence/io/concurrence.io._io.c Modules/concurrence/concurrence.io._io.c || return "$?"
    cp concurrence.dir/lib/concurrence/io/io_base.c \
       concurrence.dir/lib/concurrence/io/io_base.h \
       Modules/concurrence/ || return "$?"
    enable_module _concurrence_io_io || return "$?"

    generate_loader_py _concurrence_database_mysql_mysql concurrence.database.mysql._mysql || return "$?"
    run_pyrexc -I concurrence.dir/lib/concurrence/io concurrence.dir/lib/concurrence/database/mysql/concurrence.database.mysql._mysql.pyx || return "$?"
    patch_and_copy_cext concurrence.dir/lib/concurrence/database/mysql/concurrence.database.mysql._mysql.c Modules/concurrence/concurrence.database.mysql._mysql.c || return "$?"
    enable_module _concurrence_database_mysql_mysql || return "$?"

  ) || return "$?"
}

patchpycrypto() {
  test "$IS_CO" || return 0
  ( cd "$BUILDDIR" || return "$?"
    rm -rf pycrypto-* pycrypto.dir Lib/Crypto Modules/pycrypto || return "$?"
    tar xzvf ../pycrypto-2.3.tar.gz || return "$?"
    mv pycrypto-2.3 pycrypto.dir || return "$?"
    mkdir Lib/Crypto Modules/pycrypto Modules/pycrypto/libtom || return "$?"
    # TODO(pts): Fail if any of the pipe commands fail.
    (cd pycrypto.dir/lib && tar c $(find Crypto -type f -iname '*.py')) |
        (cd Lib && tar x) || return "$?"

    ln -s _Crypto_Cipher_DES.c Modules/pycrypto/DES.c || return "$?"
    cp pycrypto.dir/src/hash_template.c \
       pycrypto.dir/src/block_template.c \
       pycrypto.dir/src/stream_template.c \
       pycrypto.dir/src/pycrypto_compat.h \
       pycrypto.dir/src/_counter.h \
       pycrypto.dir/src/Blowfish-tables.h \
       pycrypto.dir/src/cast5.c \
       Modules/pycrypto/ || return "$?"
    cp pycrypto.dir/src/libtom/tomcrypt_des.c \
       pycrypto.dir/src/libtom/*.h \
       Modules/pycrypto/libtom/ || return "$?"

    local M CEXT_MODNAME
    for M in Crypto.Hash.MD2 Crypto.Hash.MD4 Crypto.Hash.SHA256 \
             Crypto.Hash.RIPEMD160 \
             Crypto.Cipher.AES Crypto.Cipher.ARC2 Crypto.Cipher.Blowfish \
             Crypto.Cipher.CAST Crypto.Cipher.DES Crypto.Cipher.DES3 \
             Crypto.Cipher.ARC4 Crypto.Cipher.XOR \
             Crypto.Util.strxor Crypto.Util._counter; do \
      CEXT_MODNAME="${M##*/}"
      CEXT_MODNAME="${CEXT_MODNAME//._/_}"
      CEXT_MODNAME="${CEXT_MODNAME//./_}"
      CEXT_MODNAME=_"${CEXT_MODNAME#_}"
      generate_loader_py "$CEXT_MODNAME" "$M" || return "$?"
      patch_and_copy_cext "pycrypto.dir/src/${M##*.}.c" Modules/pycrypto/"$CEXT_MODNAME".c || return "$?"
      enable_module "$CEXT_MODNAME" || return "$?"
    done

    perl -0777 -pi -e 's@ Py_InitModule\("Crypto[.]\w+[.]"@ Py_InitModule(""@g' \
        Modules/pycrypto/hash_template.c \
        Modules/pycrypto/stream_template.c \
        Modules/pycrypto/block_template.c || return "$?"

  ) || return "$?"
}

patchaloaes() {
  test "$IS_CO" || return 0
  ( cd "$BUILDDIR" || return "$?"
    rm -rf aloaes-* aloaes.dir Lib/aes Modules/aloaes || return "$?"
    tar xzvf ../alo-aes-0.3.tar.gz || return "$?"
    mv alo-aes-0.3 aloaes.dir || return "$?"
    mkdir Lib/aes Modules/aloaes || return "$?"
    cp aloaes.dir/aes/*.py Lib/aes/ || return "$?"
    generate_loader_py _aes_aes aes._aes || return "$?"
    patch_and_copy_cext aloaes.dir/aes/aesmodule.c Modules/aloaes/_aes_aes.c || return "$?"
    cp aloaes.dir/aes/rijndael-alg-fst.c \
       aloaes.dir/aes/rijndael-alg-fst.h \
       Modules/aloaes/ || return "$?"
    enable_module _aes_aes || return "$?"
  ) || return "$?"
}

patchlocale() {
  # TODO(pts): Make this idempotent.
  ( cd "$BUILDDIR" || return "$?"
    if test "$UNAME" = Darwin; then
      # To make Python able to start up with `export LC_CTYPE=utf-8', which
      # is a useful setting on the Mac OS X.
      if test "$IS_PY3"; then
        (cd Lib && $PATCH -p1 <../../locale.darwin.3.2.patch) || return "$?"
      else
        # Test it with: ./python2.7-static -c 'import locale; print locale.getpreferredencoding()'
        (cd Lib && $PATCH -p1 <../../locale.darwin.2.7.patch) || return "$?"
      fi
    fi
  ) || return "$?"
}

makeminipython() {
  test "$IS_CO" || return 0
  ( cd "$BUILDDIR" || return "$?"
    # TODO(pts): Disable co modules in Modules/Setup
    if test "$UNAME" = Darwin; then
      make python.exe || return "$?"
      mv -f python.exe minipython || return "$?"
    else
      make python || return "$?"
      mv -f python minipython || return "$?"
    fi
    $STRIP minipython || return "$?"
  ) || return "$?"
}

makepython() {
  ( cd "$BUILDDIR" || return "$?"
    if test "$UNAME" = Darwin; then
      make python.exe || return "$?"
    else
      make python || return "$?"
      rm -f python.exe || return "$?"
      ln -s python python.exe || return "$?"
    fi
  ) || return "$?"
}

buildpythonlibzip() {
  # This step doesn't depend on makepython.
  ( set -ex
    IFS='
'
    cd "$BUILDDIR" ||
    (test -f xlib.zip && mv xlib.zip xlib.zip.old) || return "$?"
    rm -rf xlib || return "$?"
    # Compatibility note: `cp -a' works on Linux, but not on Mac OS X, so
    # we use `cp -R' here which works on both.
    cp -R Lib xlib || return "$?"
    rm -f $(find xlib -iname '*.pyc') || return "$?"
    rm -f xlib/plat-*/regen
    rm -rf xlib/email/test xlib/bdddb xlib/ctypes xlib/distutils \
           xlib/idlelib xlib/lib-tk xlib/lib2to3 xlib/msilib \
           xlib/plat-aix* xlib/plat-atheos xlib/plat-beos* \
           xlib/plat-freebsd* xlib/plat-irix* xlib/plat-unixware* \
           xlib/plat-mac xlib/plat-netbsd* xlib/plat-next* \
           xlib/plat-os2* xlib/plat-riscos xlib/plat-sunos* \
           xlib/site-packages* xlib/sqlite3/test/* xlib/turtle* xlib/tkinter \
           xlib/bsddb/test \
           xlib/test xlib/*.egg-info || return "$?"
    if test "$UNAME" = Darwin; then
      rm -rf xlib/plat-linux2 || return "$?"
    else
      rm -rf xlib/plat-darwin || return "$?"
    fi
    if test "$IS_PY3"; then
      cp ../site.3.2.py xlib/site.py || return "$?"
      # This is to make `import socket; socket.gethostbyname('www.google.com')
      # work.
      (cd xlib && $PATCH -p1 <../../encodings_idna_missing_unicodedata.3.2.patch) || return "$?"
    else
      cp ../site.2.7.py xlib/site.py || return "$?"
    fi
    cd xlib || return "$?"
    rm -f *~ */*~ || return "$?"
    rm -f ../xlib.zip || return "$?"
    run_mkzip ../xlib.zip * || return "$?"
  ) || return "$?"
}

# Fix ELF binaries to contain GNU/Linux as the operating system. This is
# needed when running the program on FreeBSD in Linux mode.
do_elfosfix() {
  perl -e'
use integer;
use strict;

#** ELF operating system codes from FreeBSDs /usr/share/misc/magic
my %ELF_os_codes=qw{
SYSV 0
HP-UX 1
NetBSD 2
GNU/Linux 3
GNU/Hurd 4
86Open 5
Solaris 6
Monterey 7
IRIX 8
FreeBSD 9
Tru64 10
Novell 11
OpenBSD 12
ARM 97
embedded 255
};
my $from_oscode=$ELF_os_codes{"SYSV"};
my $to_oscode=$ELF_os_codes{"GNU/Linux"};

for my $fn (@ARGV) {
  my $f;
  if (!open $f, "+<", $fn) {
    print STDERR "$0: $fn: $!\n";
    exit 2  # next
  }
  my $head;
  # vvv Imp: continue on next file instead of die()ing
  die if 8!=sysread($f,$head,8);
  if (substr($head,0,4)ne"\177ELF") {
    print STDERR "$0: $fn: not an ELF file\n";
    close($f); next;
  }
  if (vec($head,7,8)==$to_oscode) {
    print STDERR "$0: info: $fn: already fixed\n";
  }
  if ($from_oscode!=$to_oscode && vec($head,7,8)==$from_oscode) {
    vec($head,7,8)=$to_oscode;
    die if 0!=sysseek($f,0,0);
    die if length($head)!=syswrite($f,$head);
  }
  die "file error\n" if !close($f);
}' -- "$@" || return "$?"
}

buildtarget() {
  cp "$BUILDDIR"/python.exe "$BUILDDIR/$TARGET" || return "$?"
  $STRIP "$BUILDDIR/$TARGET" || return "$?"
  if test "$UNAME" = Linux; then
    do_elfosfix "$BUILDDIR/$TARGET" || return "$?"
  fi
  cat "$BUILDDIR"/xlib.zip >>"$BUILDDIR/$TARGET" || return "$?"
  cp "$BUILDDIR/$TARGET" "$TARGET" || return "$?"
  ls -l "$TARGET" || return "$?"
}

betry() {
  # This step is optional. It tries the freshly built binary.
  mkdir -p bch be/bardir || return "$?"
  echo "print 'FOO'" >be/foo.py || return "$?"
  echo "print 'BAR'" >be/bardir/bar.py || return "$?"
  cp "$TARGET" be/sp || return "$?"
  cp "$TARGET" bch/sp || return "$?"
  export PYTHONPATH=bardir
  unset PYTHONHOME
  #unset PYTHONPATH
  (cd be && ./sp) || return "$?"
}

fail_step() {
  set +ex
  echo "Failed in step $2 with code $1"
  echo "Fix and retry with: $0 ${TARGET%-static} $2 $3"
  exit "$1"
}

XSTEPS="$(echo $STEPS) "  # Collapse whitespace etc.
XSTEPS0="$XSTEPS"

for STEP in $XSTEPS; do
  echo "Running step: $STEP"
  XSTEPS="${XSTEPS#* }"
  echo "Steps remaining: $XSTEPS"
  set -x
  # set -e (abort on error) has no effect in functions in busybox sh, so we
  # don't enable it.
  if ! $STEP; then
    set +x
    fail_step "$?" "$STEP" "$XSTEPS"
  fi
  set +x
done
echo "OK running $0 ${TARGET%-static} $XSTEPS0"

exit 0

fi
