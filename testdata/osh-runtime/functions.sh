# /usr/share/abuild/functions.sh

sysconfdir=/etc
program=${0##*/}

arch_to_hostspec() {
	case "$1" in
	aarch64)	echo "aarch64-alpine-linux-musl" ;;
	armhf)		echo "armv6-alpine-linux-muslgnueabihf" ;;
	armv7)		echo "armv7-alpine-linux-musleabihf" ;;
	ppc)		echo "powerpc-alpine-linux-musl" ;;
	ppc64)		echo "powerpc64-alpine-linux-musl" ;;
	ppc64le)	echo "powerpc64le-alpine-linux-musl" ;;
	s390x)		echo "s390x-alpine-linux-musl" ;;
	x86)		echo "i586-alpine-linux-musl" ;;
	x86_64)		echo "x86_64-alpine-linux-musl" ;;
	*)		echo "unknown" ;;
	esac
}

hostspec_to_arch() {
	case "$1" in
	aarch64*-*-*-*)		echo "aarch64" ;;
	arm*-*-*-*eabi)		echo "armel" ;;
	armv6*-*-*-*eabihf)	echo "armhf" ;;
	armv7*-*-*-*eabihf)	echo "armv7" ;;
	i[0-9]86-*-*-*)		echo "x86" ;;
	powerpc-*-*-*)		echo "ppc" ;;
	powerpc64-*-*-*)	echo "ppc64" ;;
	powerpc64le-*-*-*)	echo "ppc64le" ;;
	s390x-*-*-*)		echo "s390x" ;;
	x86_64-*-*-*)		echo "x86_64" ;;
	*)			echo "unknown" ;;
	esac
}

hostspec_to_libc() {
	case "$1" in
	*-*-*-uclibc*)	echo "uclibc" ;;
	*-*-*-musl*)	echo "musl" ;;
	*-*-*-gnu*)	echo "glibc" ;;
	*)		echo "unknown" ;;
	esac
}

readconfig() {
	local _APORTSDIR _BUILDDIR _PKGDEST _SRCPKGDEST _REPODEST _SRCDEST
	local _CARCH _CHOST _CTARGET _CPPFLAGS _CFLAGS _CXXFLAGS _LDFLAGS
	local _JOBS _MAKEFLAGS _PACKAGER _USE_COLORS
	local gitbase=
	[ -n "${APORTSDIR+x}" ] && _APORTSDIR=$APORTSDIR
	[ -n "${BUILDDIR+x}" ] && _BUILDDIR=$BUILDDIR
	[ -n "${PKGDEST+x}" ] && _PKGDEST=$PKGDEST
	[ -n "${SRCPKGDEST+x}" ] && _SRCPKGDEST=$SRCPKGDEST
	[ -n "${REPODEST+x}" ] && _REPODEST=$REPODEST
	[ -n "${SRCDEST+x}" ] && _SRCDEST=$SRCDEST
	[ -n "${CARCH+x}" ] && _CARCH=$CARCH
	[ -n "${CHOST+x}" ] && _CHOST=$CHOST
	[ -n "${CTARGET+x}" ] && _CTARGET=$CTARGET
	[ -n "${CPPFLAGS+x}" ] && _CPPFLAGS=$CPPFLAGS
	[ -n "${CFLAGS+x}" ] && _CFLAGS=$CFLAGS
	[ -n "${CXXFLAGS+x}" ] && _CXXFLAGS=$CXXFLAGS
	[ -n "${LDFLAGS+x}" ] && _LDFLAGS=$LDFLAGS
	[ -n "${JOBS+x}" ] && _JOBS=$JOBS
	[ -n "${MAKEFLAGS+x}" ] && _MAKEFLAGS=$MAKEFLAGS
	[ -n "${PACKAGER+x}" ] && _PACKAGER=$PACKAGER
	[ -n "${USE_COLORS+x}" ] && _USE_COLORS="$USE_COLORS"
	: ${ABUILD_CONF:=$sysconfdir/abuild.conf}
	: ${ABUILD_USERDIR:=$HOME/.abuild}
	: ${ABUILD_USERCONF:=$ABUILD_USERDIR/abuild.conf}
	[ -f "$ABUILD_CONF" ] && . "$ABUILD_CONF"
	[ -f "$ABUILD_USERCONF" ] && . "$ABUILD_USERCONF"
	APORTSDIR=${_APORTSDIR-$APORTSDIR}
	gitbase=$(git rev-parse --show-toplevel 2>/dev/null) || true # already is -P
	if [ -d "$APORTSDIR" ]; then
		APORTSDIR=$(cd "$APORTSDIR"; pwd -P)
	elif [ -z "$APORTSDIR" ] && [ -d "$HOME/aports" ]; then
		APORTSDIR=$(cd "$HOME/aports"; pwd -P)
	else
		if [ -n "$gitbase" ]; then
			case $(git config remote.origin.url) in
			*/aports) APORTSDIR=$gitbase ;;
			*) APORTSDIR= ;;
			esac
		else
			APORTSDIR=
		fi
	fi
	# source any .abuild file at the aports root, but only if we are currently in aports tree
	[ -n "$APORTSDIR" ] && [ -f "$APORTSDIR/.abuild" ] && [ "$APORTSDIR" = "$gitbase" ] && . "$APORTSDIR/.abuild"
	BUILDDIR=${_BUILDDIR-$BUILDDIR}
	PKGDEST=${_PKGDEST-$PKGDEST}
	SRCPKGDEST=${_SRCPKGDEST-$SRCPKGDEST}
	REPODEST=${_REPODEST-$REPODEST}
	SRCDEST=${_SRCDEST-$SRCDEST}
	CARCH=${_CARCH-$CARCH}
	CHOST=${_CHOST-$CHOST}
	CTARGET=${_CTARGET-$CTARGET}
	CPPFLAGS=${_CPPFLAGS-$CPPFLAGS}
	CFLAGS=${_CFLAGS-$CFLAGS}
	CXXFLAGS=${_CXXFLAGS-$CXXFLAGS}
	LDFLAGS=${_LDFLAGS-$LDFLAGS}
	JOBS=${_JOBS-$JOBS}
	MAKEFLAGS=${_MAKEFLAGS-$MAKEFLAGS}
	PACKAGER=${_PACKAGER-$PACKAGER}
	USE_COLORS=${_USE_COLORS-$USE_COLORS}

	[ -z "$CBUILD" ] && CBUILD="$(gcc -dumpmachine)"
	[ -z "$CHOST" ] && CHOST="$CBUILD"
	[ -z "$CTARGET" ] && CTARGET="$CHOST"
	[ "$(arch_to_hostspec $CBUILD)" != "unknown" ] && CBUILD="$(arch_to_hostspec $CBUILD)"
	[ "$(arch_to_hostspec $CHOST)" != "unknown" ] && CHOST="$(arch_to_hostspec $CHOST)"
	[ "$(arch_to_hostspec $CTARGET)" != "unknown" ] && CTARGET="$(arch_to_hostspec $CTARGET)"

	[ -z "$CARCH" ] && CARCH="$(hostspec_to_arch $CHOST)"
	[ -z "$CLIBC" ] && CLIBC="$(hostspec_to_libc $CHOST)"
	[ -z "$CBUILD_ARCH" ] && CBUILD_ARCH="$(hostspec_to_arch $CBUILD)"
	[ -z "$CTARGET_ARCH" ] && CTARGET_ARCH="$(hostspec_to_arch $CTARGET)"
	[ -z "$CTARGET_LIBC" ] && CTARGET_LIBC="$(hostspec_to_libc $CTARGET)"

	if [ "$CHOST" != "$CTARGET" ]; then
		# setup environment for creating cross compiler
		[ -z "$CBUILDROOT" ] && export CBUILDROOT="$HOME/sysroot-$CTARGET_ARCH/"
	elif [ "$CBUILD" != "$CHOST" ]; then
		# setup build root
		[ -z "$CBUILDROOT" ] && export CBUILDROOT="$HOME/sysroot-$CTARGET_ARCH/"
		# prepare pkg-config for cross building
		[ -z "$PKG_CONFIG_PATH" ] && export PKG_CONFIG_PATH="${CBUILDROOT}/usr/lib/pkgconfig/"
		[ -z "$PKG_CONFIG_SYSROOT_DIR" ] && export PKG_CONFIG_SYSROOT_DIR="${CBUILDROOT}"
		# libtool bug workaround for extra rpaths
		[ -z "$lt_cv_sys_lib_dlsearch_path_spec" ] && \
			export lt_cv_sys_lib_dlsearch_path_spec="${CBUILDROOT}/lib ${CBUILDROOT}/usr/lib /usr/lib /lib /usr/local/lib"
		# setup cross-compiler
		if [ -z "$CROSS_COMPILE" ]; then
			export CROSS_COMPILE="${CHOST}-"
			export HOSTCC="$CC"
			export HOSTCXX="$CXX"
			export HOSTLD="$LD"
			export HOSTCPPFLAGS="$CPPFLAGS"
			export HOSTCXXFLAGS="$CXXFLAGS"
			export HOSTCFLAGS="$CFLAGS"
			export HOSTLDFLAGS="$LDFLAGS"
			export CC=${CROSS_COMPILE}gcc
			export CXX=${CROSS_COMPILE}g++
			export LD=${CROSS_COMPILE}ld
			export CPPFLAGS="--sysroot=${CBUILDROOT} $CPPFLAGS"
			export CXXFLAGS="--sysroot=${CBUILDROOT} $CXXFLAGS"
			export CFLAGS="--sysroot=${CBUILDROOT} $CFLAGS"
			export LDFLAGS="--sysroot=${CBUILDROOT} $LDFLAGS"
		fi
	fi
}
readconfig

# expects $1 to be a package directory in the aports tree ('foo' or 'main/foo')
# outputs APKBUILD's path if successful
aports_buildscript() {
	[ -n "$APORTSDIR" ] || return 1
	if [ "${1#*/}" != "$1" ]; then
		( cd "$APORTSDIR/$1" && [ -f APKBUILD ] && echo "$PWD/APKBUILD" )
	else
		( cd "$APORTSDIR"/*/"$1" && [ -f APKBUILD ] && echo "$PWD/APKBUILD" )
	fi
}

# expects $1 to be a file, or a directory containing an APKBUILD, or a package directory in the aports tree
# outputs APKBUILD's path if successful (doesn't verify that it's a valid APKBUILD)
any_buildscript() {
	if [ -f "$1" ]; then
		echo "$1"
	elif [ -d "$1" ]; then
		[ -f "$1/APKBUILD" ] || return 1
		echo "$1/APKBUILD"
	else
		aports_buildscript "$1" || return 1
	fi
}

# output functions
msg() {
	[ -n "$quiet" ] && return 0
	local prompt="$GREEN>>>${NORMAL}"
	printf "${prompt} %s\n" "$1" >&2
}

msg2() {
	[ -n "$quiet" ] && return 0
	#      ">>> %s"
	printf "    %s\n" "$1" >&2
}

warning() {
	local prompt="${YELLOW}>>> WARNING:${NORMAL}"
	printf "${prompt} %s\n" "$1" >&2
}

warning2() {
	#      ">>> WARNING: %s\n"
	printf "             %s\n" "$1" >&2
}

error() {
	local prompt="${RED}>>> ERROR:${NORMAL}"
	printf "${prompt} %s\n" "$1" >&2
}

error2() {
	#      ">>> ERROR:
	printf "           %s\n" "$1" >&2
}

set_xterm_title() {
	if [ "$TERM" = xterm ] && [ -n "$USE_COLORS" ]; then
		 printf "\033]0;$1\007" >&2
	fi
}

disable_colors() {
	NORMAL=""
	STRONG=""
	RED=""
	GREEN=""
	YELLOW=""
	BLUE=""
}

enable_colors() {
	NORMAL="\033[1;0m"
	STRONG="\033[1;1m"
	RED="\033[1;31m"
	GREEN="\033[1;32m"
	YELLOW="\033[1;33m"
	BLUE="\033[1;34m"
}

if [ -n "$USE_COLORS" ] && [ -t 1 ]; then
	enable_colors
else
	disable_colors
fi

# caller may override
cleanup() {
	return 0
}

die() {
	error "$@"
	cleanup
	exit 1
}
