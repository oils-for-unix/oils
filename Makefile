# Build App Bundles.

# Needed for rules with '> $@'.  Does this always work?
.DELETE_ON_ERROR:

# Intermediate targets aren't automatically deleted.
.SECONDARY:

# Do this before every build.  There should be a nicer way of handling
# directories but I don't know it.
$(shell mkdir -p _bin _release _build/hello _build/oil)

# What the end user should build when they type 'make'.
default: _bin/oil.ovm

# Debug bundles and release tarballs.
all: \
	_bin/hello.ovm _bin/oil.ovm \
	_bin/hello.ovm-dbg _bin/oil.ovm-dbg \
	_release/hello.tar _release/oil.tar

clean:
	rm -r -f _build/hello _build/oil
	rm -f _bin/oil.* _bin/hello.* _build/runpy-deps-*.txt _build/c-module-toc.txt
	build/actions.sh clean-pyc

.PHONY: default all clean

PY27 = Python-2.7.13

# What files correspond to each C module.
# TODO:
# - Where to put -l z?  (Done in Modules/Setup.dist)
_build/c-module-toc.txt: build/c_module_toc.py
	build/actions.sh c-module-toc > $@

# Python and C dependencies of runpy.
# NOTE: This is done with a pattern rule because of the "multiple outputs"
# problem in Make.
_build/runpy-deps-%.txt: build/runpy_deps.py
	build/actions.sh runpy-deps _build

#
# Hello App.  Everything below here is app-specific.
#

# C module dependencies
-include _build/hello/ovm.d

# What Python module to run.
_build/hello/main_name.c:
	echo 'char* MAIN_NAME = "hello";' > $@

# Dependencies calculated by importing main.  The guard is because ovm.d
# depends on it.  Is that correct?  We'll skip it before 'make dirs'.
_build/hello/app-deps-%.txt: $(HELLO_SRCS) build/app_deps.py
	test -d _build/hello && \
		build/actions.sh app-deps hello build/testdata hello

# NOTE: We could use src/dest paths pattern instead of _build/app?
#
# TODO:
# - Deps need to be better.  Depend on .pyc and .py.    I guess
#   app-deps hello will compile the .pyc files.  Don't need a separate action.
#   %.pyc : %py
_build/hello/bytecode.zip: $(HELLO_SRCS) \
                           build/hello-manifest.txt \
                           _build/hello/app-deps-py.txt \
                           _build/runpy-deps-py.txt
	build/make_zip.py $@ \
	  build/hello-manifest.txt _build/hello/app-deps-py.txt _build/runpy-deps-py.txt

#
# Oil
#

# C module dependencies
-include _build/oil/ovm.d

_build/oil/main_name.c:
	echo 'char* MAIN_NAME = "bin.oil";' > $@

# Dependencies calculated by importing main.
_build/oil/app-deps-%.txt: build/app_deps.py
	test -d _build/hello && \
		build/actions.sh app-deps oil ~/git/oil bin.oil

# TODO: Need $(OIL_SRCS) here?
_build/oil/bytecode.zip: build/oil-manifest.txt \
  	                     _build/oil/app-deps-py.txt \
                         _build/runpy-deps-py.txt
	build/make_zip.py $@ \
		build/oil-manifest.txt _build/oil/app-deps-py.txt _build/runpy-deps-py.txt

#
# App-Independent Pattern Rules.
#

# Regenerate dependencies.  But only if we made the app dirs.
_build/%/ovm.d: _build/%/app-deps-c.txt
	build/actions.sh make-dotd $* $^ > $@

# A trick: remove the first dep to form the lists.  You can't just use $^
# because './c_module_srcs.py' is rewritten to 'c_module_srcs.py'.
_build/%/c-module-srcs.txt: \
	build/c_module_srcs.py _build/c-module-toc.txt _build/%/app-deps-c.txt
	build/c_module_srcs.py $(filter-out $<,$^) > $@

_build/%/all-deps-c.txt: build/static-c-modules.txt _build/%/app-deps-c.txt
	build/actions.sh join-modules $^ > $@

# Per-app extension module initialization.
_build/%/module_init.c: $(PY27)/Modules/config.c.in _build/%/all-deps-c.txt
	cat _build/$*/all-deps-c.txt | xargs build/actions.sh gen-module-init > $@

# Release build.
# This depends on the static modules
_build/%/ovm: _build/%/module_init.c _build/%/main_name.c _build/%/c-module-srcs.txt
	build/compile.sh build-opt $@ $^

# Fast build, with symbols for debugging.
_build/%/ovm-dbg: _build/%/module_init.c _build/%/main_name.c _build/%/c-module-srcs.txt
	build/compile.sh build-dbg $@ $^

# Coverage, for paring down the files that we build.
# TODO: Hook this up.
_build/%/ovm-cov: _build/%/module_init.c _build/%/main_name.c _build/%/c-module-srcs.c
	build/compile.sh build $@ $^

# Make bundles quickly.
_bin/%.ovm-dbg: _build/%/ovm-dbg _build/%/bytecode.zip
	cat $^ > $@
	chmod +x $@

_bin/%.ovm: _build/%/ovm _build/%/bytecode.zip
	cat $^ > $@
	chmod +x $@

# Makefile, shell scripts, discovered .c and .py deps, app source.

# TODO:
# - Why does putting c_module_srcs.txt here mess it up?
_release/%.tar: _build/%/bytecode.zip \
	              _build/%/module_init.c \
								_build/%/main_name.c
	build/compile.sh make-tar $* $@

# For debugging
print-%:
	@echo $*=$($*)
