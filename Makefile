# Build OVM App Bundles (Python code with a statically-linked CPython
# interpreter.)
#
# We also build a tarball that allows the end user to build an app bundle.
# They need GNU Make, bash, and a C compiler.  (And xargs, chmod, etc.)
#
# Tarball layout (see build/compile.sh for details):
#
# oil.tar/
#   configure
#   install
#   Makefile
#   _build/                 # Intermediate files
#     oil/                  # The app name
#       bytecode-opy.zip        # Arch-independent
#       main_name.c
#       module_init.c       # Python module initializer
#       c-module-srcs.txt   # List of Modules/ etc.
#   native/                 # App-specific modules
#     libc.c
#   build/
#     static-c-modules.txt  # From Python interpreter
#     compile.sh ...
#     detect-cc.c ...
#   Python-2.7.13/
#     pyconfig.h            # A frozen version
#     Python/
#     Objects/
#     Modules/
#     Include/
#
#
# Intermediate layout:
#
# _build/
#   cpython-full/           # Full CPython build, for dynamically
#                           # discovering Python/C dependencies
#   c-module-toc.txt        # What files each module is in
#   oil/                    # App-specific dir
#     py-to-compile.txt
#     all-deps-py.txt       # input to compiler: _build/py-to-compile +
                            # _build/oil/py-to-compile
#     opy-app-deps.txt      # compiled with OPy, name DOESN'T match app-deps-% !
#     all-deps-c.txt        # App deps plus CPython platform deps
#     app-deps-cpython.txt  # compiled with CPython
#     bytecode-cpython.zip
#     bytecode-opy.zip
#     c-module-srcs.txt
#     main_name.c
#     module_init.c
#     ovm.d                 # Make fragment
#     ovm, ovm-dbg          # OVM executables (without bytecode)
# _release/
#   oil.tar                 # See tarball layout above
# _bin/                     # Concatenated App Bundles
#   oil.ovm
#   oil.ovm-dbg
#   hello.ovm
#   hello.ovm-dbg

# Needed for rules with '> $@'.  Does this always work?
.DELETE_ON_ERROR:

# Intermediate targets aren't automatically deleted.
.SECONDARY:

# Don't use the built-in rules database.  This makes the 'make -d' output
# easier to read.
.SUFFIXES:

# Make all directories before every build.  There might be a nicer way of
# handling directories but I don't know it.
# NOTE: _devbuild is made by build/dev.sh.  That directory is NOT cleaned with
# 'make clean'.
$(shell mkdir -p _bin _release _tmp _build/hello _build/oil _build/opy)

ACTIONS_SH := build/actions.sh
COMPILE_SH := build/compile.sh

# Change the bytecode compiler here.
#BYTECODE_ZIP := bytecode-cpython.zip
BYTECODE_ZIP := bytecode-opy.zip

# We want to generated the unstripped binary first, then strip it, so we can
# retain symbols.  There doesn't seem to be a portable way to do this?
#
# The GNU toolchain has objcopy, and Clang has dsymutil.

HAVE_OBJCOPY := $(shell command -v objcopy 2>/dev/null)

# For faster tesing of builds
#default: _bin/oil.ovm-dbg

# What the end user should build when they type 'make'.
default: _bin/oil.ovm

# Debug bundles and release tarballs.
all: \
	_bin/hello.ovm _bin/oil.ovm \
	_bin/hello.ovm-dbg _bin/oil.ovm-dbg \
	_release/hello.tar _release/oil.tar

# For the release tarball.
clean:
	$(ACTIONS_SH) clean-source-tarball-build

# For developers in a repo.
clean-repo:
	$(ACTIONS_SH) clean-repo

# .PHONY alias for compatibility
install:
	@./install

uninstall:
	@./uninstall

.PHONY: default all clean clean-repo install uninstall

# For debugging
print-%:
	@echo $*=$($*)

# These files is intentionally NOT included in release tarballs.  For example,
# we don't want try to rebuild _build/oil/bytecode-opy.zip, which is already
# included in the release tarball.  Portable rules can be run on the developer
# machine rather than on the end-user machine.

-include portable-rules.mk  # Must come first
-include build/hello.mk
-include build/oil.mk
-include build/opy.mk

#
# Native Builds
#

# Release build.
# This depends on the static modules
_build/%/ovm-opt: _build/%/module_init.c _build/%/main_name.c \
                  _build/%/c-module-srcs.txt $(COMPILE_SH)
	$(COMPILE_SH) build-opt $@ $(filter-out $(COMPILE_SH),$^)


ifdef HAVE_OBJCOPY

# If possible, we want symbols for OPTIMIZED builds, for various profiling
# tools.

# First copy the symbols out of the binary we built.
# (Distro packagers might use this to create symbols packages?)
_build/%/ovm-opt.symbols: _build/%/ovm-opt
	objcopy --only-keep-debug $^ $@

# Then create a stripped binary that LINKS to the symbols.

_build/%/ovm-opt.stripped: _build/%/ovm-opt _build/%/ovm-opt.symbols
	strip -o $@ _build/$*/ovm-opt  # What's the difference with debug symbols?
	# We need a relative path since it will be _bin/oil.ovm
	objcopy --add-gnu-debuglink=_build/$*/ovm-opt.symbols $@

else

# We don't have objcopy, which means we might be using the Clang toolchain
# (e.g. on OS X).  We're not doing any profiling on OS X, and there's no way to
# link the symbols, so just strip it.
#
# We used to have 'dsymutil' but it was never tested.
# https://stackoverflow.com/a/33307778

_build/%/ovm-opt.stripped: _build/%/ovm-opt
	strip -o $@ _build/$*/ovm-opt 

endif

# Fast build, with symbols for debugging.
_build/%/ovm-dbg: _build/%/module_init.c _build/%/main_name.c \
                  _build/%/c-module-srcs.txt $(COMPILE_SH)
	$(COMPILE_SH) build-dbg $@ $(filter-out $(COMPILE_SH),$^)

# Coverage, for paring down the files that we build.
# TODO: Hook this up.
_build/%/ovm-cov: _build/%/module_init.c _build/%/main_name.c \
                  _build/%/c-module-srcs.txt $(COMPILE_SH)
	$(COMPILE_SH) build $@ $(filter-out $(COMPILE_SH),$^)

# App bundles.
_bin/%.ovm-dbg: _build/%/ovm-dbg _build/%/$(BYTECODE_ZIP)
	cat $^ > $@
	chmod +x $@

_bin/%.ovm: _build/%/ovm-opt.stripped _build/%/$(BYTECODE_ZIP)
	cat $^ > $@
	chmod +x $@

# Optimized version with symbols.
_bin/%.ovm-opt: _build/%/ovm-opt _build/%/$(BYTECODE_ZIP)
	cat $^ > $@
	chmod +x $@
